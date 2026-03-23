from __future__ import annotations

import base64
import ctypes
import json
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ctypes import wintypes


class CookieImportError(RuntimeError):
    pass


@dataclass
class ImportedCookieJar:
    browser: str
    cookie_header: str
    cookie_count: int
    profile_path: str


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


class BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.ULONG),
        ("dwInfoVersion", wintypes.ULONG),
        ("pbNonce", ctypes.POINTER(ctypes.c_ubyte)),
        ("cbNonce", wintypes.ULONG),
        ("pbAuthData", ctypes.POINTER(ctypes.c_ubyte)),
        ("cbAuthData", wintypes.ULONG),
        ("pbTag", ctypes.POINTER(ctypes.c_ubyte)),
        ("cbTag", wintypes.ULONG),
        ("pbMacContext", ctypes.POINTER(ctypes.c_ubyte)),
        ("cbMacContext", wintypes.ULONG),
        ("cbAAD", wintypes.ULONG),
        ("cbData", ctypes.c_ulonglong),
        ("dwFlags", wintypes.ULONG),
    ]


crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32
bcrypt = ctypes.windll.bcrypt

crypt32.CryptUnprotectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    ctypes.POINTER(ctypes.c_wchar_p),
    ctypes.POINTER(DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB),
]
crypt32.CryptUnprotectData.restype = wintypes.BOOL
kernel32.LocalFree.argtypes = [ctypes.c_void_p]
kernel32.LocalFree.restype = ctypes.c_void_p

bcrypt.BCryptOpenAlgorithmProvider.argtypes = [
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.ULONG,
]
bcrypt.BCryptOpenAlgorithmProvider.restype = wintypes.ULONG
bcrypt.BCryptCloseAlgorithmProvider.argtypes = [ctypes.c_void_p, wintypes.ULONG]
bcrypt.BCryptCloseAlgorithmProvider.restype = wintypes.ULONG
bcrypt.BCryptSetProperty.argtypes = [
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    ctypes.c_void_p,
    wintypes.ULONG,
    wintypes.ULONG,
]
bcrypt.BCryptSetProperty.restype = wintypes.ULONG
bcrypt.BCryptGetProperty.argtypes = [
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    ctypes.c_void_p,
    wintypes.ULONG,
    ctypes.POINTER(wintypes.ULONG),
    wintypes.ULONG,
]
bcrypt.BCryptGetProperty.restype = wintypes.ULONG
bcrypt.BCryptGenerateSymmetricKey.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.c_void_p,
    wintypes.ULONG,
    ctypes.c_void_p,
    wintypes.ULONG,
    wintypes.ULONG,
]
bcrypt.BCryptGenerateSymmetricKey.restype = wintypes.ULONG
bcrypt.BCryptDestroyKey.argtypes = [ctypes.c_void_p]
bcrypt.BCryptDestroyKey.restype = wintypes.ULONG
bcrypt.BCryptDecrypt.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.ULONG,
    ctypes.POINTER(BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO),
    ctypes.c_void_p,
    wintypes.ULONG,
    ctypes.c_void_p,
    wintypes.ULONG,
    ctypes.POINTER(wintypes.ULONG),
    wintypes.ULONG,
]
bcrypt.BCryptDecrypt.restype = wintypes.ULONG


STATUS_SUCCESS = 0
BCRYPT_AUTH_MODE_INFO_VERSION = 1
BCRYPT_AES_ALGORITHM = "AES"
BCRYPT_CHAIN_MODE_GCM = "ChainingModeGCM"
BCRYPT_CHAINING_MODE = "ChainingMode"
BCRYPT_OBJECT_LENGTH = "ObjectLength"


CHROMIUM_SOURCES = {
    "edge": {
        "user_data_dir": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data",
        "state_path": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data" / "Local State",
    },
    "chrome": {
        "user_data_dir": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data",
        "state_path": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data" / "Local State",
    },
}

FIREFOX_PROFILES_DIR = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"


def _check_status(status: int, action: str) -> None:
    if status != STATUS_SUCCESS:
        raise CookieImportError(f"{action} failed with NTSTATUS 0x{status:08x}")


def _dpapi_unprotect(data: bytes) -> bytes:
    if not data:
        return b""
    input_buffer = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    algorithm = ctypes.c_void_p()
    key_handle = ctypes.c_void_p()
    key_object = None
    try:
        _check_status(
            bcrypt.BCryptOpenAlgorithmProvider(ctypes.byref(algorithm), BCRYPT_AES_ALGORITHM, None, 0),
            "BCryptOpenAlgorithmProvider",
        )

        chaining_mode = ctypes.create_unicode_buffer(BCRYPT_CHAIN_MODE_GCM)
        _check_status(
            bcrypt.BCryptSetProperty(
                algorithm,
                BCRYPT_CHAINING_MODE,
                ctypes.cast(chaining_mode, ctypes.c_void_p),
                ctypes.sizeof(chaining_mode),
                0,
            ),
            "BCryptSetProperty",
        )

        object_length = wintypes.ULONG()
        result_length = wintypes.ULONG()
        _check_status(
            bcrypt.BCryptGetProperty(
                algorithm,
                BCRYPT_OBJECT_LENGTH,
                ctypes.byref(object_length),
                ctypes.sizeof(object_length),
                ctypes.byref(result_length),
                0,
            ),
            "BCryptGetProperty",
        )

        key_object = ctypes.create_string_buffer(object_length.value)
        key_buffer = ctypes.create_string_buffer(key, len(key))
        _check_status(
            bcrypt.BCryptGenerateSymmetricKey(
                algorithm,
                ctypes.byref(key_handle),
                key_object,
                object_length.value,
                key_buffer,
                len(key),
                0,
            ),
            "BCryptGenerateSymmetricKey",
        )

        nonce_buffer = ctypes.create_string_buffer(nonce, len(nonce))
        tag_buffer = ctypes.create_string_buffer(tag, len(tag))
        cipher_buffer = ctypes.create_string_buffer(ciphertext, len(ciphertext))

        auth_info = BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO()
        auth_info.cbSize = ctypes.sizeof(BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO)
        auth_info.dwInfoVersion = BCRYPT_AUTH_MODE_INFO_VERSION
        auth_info.pbNonce = ctypes.cast(nonce_buffer, ctypes.POINTER(ctypes.c_ubyte))
        auth_info.cbNonce = len(nonce)
        auth_info.pbTag = ctypes.cast(tag_buffer, ctypes.POINTER(ctypes.c_ubyte))
        auth_info.cbTag = len(tag)

        output_length = wintypes.ULONG()
        _check_status(
            bcrypt.BCryptDecrypt(
                key_handle,
                cipher_buffer,
                len(ciphertext),
                ctypes.byref(auth_info),
                None,
                0,
                None,
                0,
                ctypes.byref(output_length),
                0,
            ),
            "BCryptDecrypt(size)",
        )

        output_buffer = ctypes.create_string_buffer(output_length.value)
        _check_status(
            bcrypt.BCryptDecrypt(
                key_handle,
                cipher_buffer,
                len(ciphertext),
                ctypes.byref(auth_info),
                None,
                0,
                output_buffer,
                output_length.value,
                ctypes.byref(output_length),
                0,
            ),
            "BCryptDecrypt",
        )
        return output_buffer.raw[: output_length.value]
    finally:
        if key_handle:
            bcrypt.BCryptDestroyKey(key_handle)
        if algorithm:
            bcrypt.BCryptCloseAlgorithmProvider(algorithm, 0)


def _decrypt_chromium_value(encrypted_value: bytes, master_key: bytes) -> str:
    if not encrypted_value:
        return ""
    if encrypted_value.startswith((b"v10", b"v11", b"v20")):
        nonce = encrypted_value[3:15]
        ciphertext = encrypted_value[15:-16]
        tag = encrypted_value[-16:]
        return _aes_gcm_decrypt(master_key, nonce, ciphertext, tag).decode("utf-8", errors="ignore")
    return _dpapi_unprotect(encrypted_value).decode("utf-8", errors="ignore")


def _copy_sqlite_db(db_path: Path) -> str:
    temp_dir = tempfile.mkdtemp(prefix="reader_cookie_")
    temp_path = Path(temp_dir) / db_path.name
    shutil.copy2(db_path, temp_path)
    return str(temp_path)


def _query_sqlite_rows(db_path: Path, query: str, params: tuple) -> list[tuple]:
    sqlite_uri = f"file:{db_path.as_posix()}?mode=ro&immutable=1"
    try:
        with sqlite3.connect(sqlite_uri, uri=True) as conn:
            return conn.execute(query, params).fetchall()
    except sqlite3.Error:
        temp_db = _copy_sqlite_db(db_path)
        try:
            with sqlite3.connect(temp_db) as conn:
                return conn.execute(query, params).fetchall()
        finally:
            shutil.rmtree(Path(temp_db).parent, ignore_errors=True)


def _load_chromium_master_key(state_path: Path) -> bytes:
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    encrypted_key = base64.b64decode(state["os_crypt"]["encrypted_key"])
    if encrypted_key.startswith(b"DPAPI"):
        encrypted_key = encrypted_key[5:]
    try:
        return _dpapi_unprotect(encrypted_key)
    except OSError as exc:
        raise CookieImportError(
            "Current browser master key could not be decrypted in this Windows session."
        ) from exc


def _iter_chromium_cookie_dbs(user_data_dir: Path):
    for profile in sorted(user_data_dir.iterdir()):
        if not profile.is_dir():
            continue
        if profile.name != "Default" and not profile.name.startswith("Profile"):
            continue
        for candidate in (profile / "Network" / "Cookies", profile / "Cookies"):
            if candidate.exists():
                yield profile, candidate
                break


def _build_cookie_header(cookie_pairs: dict[str, str]) -> str:
    return "; ".join(f"{name}={value}" for name, value in cookie_pairs.items() if value)


def import_chromium_cookies(browser: str, domain: str) -> ImportedCookieJar:
    source = CHROMIUM_SOURCES.get(browser)
    if not source:
        raise CookieImportError(f"Unsupported Chromium browser: {browser}")

    user_data_dir = source["user_data_dir"]
    state_path = source["state_path"]
    if not state_path.exists() or not user_data_dir.exists():
        raise CookieImportError(f"{browser} profile was not found on this machine")

    master_key = _load_chromium_master_key(state_path)
    collected: dict[str, str] = {}
    profile_path = ""

    for profile, db_path in _iter_chromium_cookie_dbs(user_data_dir):
        rows = _query_sqlite_rows(
            db_path,
            """
            SELECT name, value, encrypted_value
            FROM cookies
            WHERE host_key LIKE ?
            ORDER BY LENGTH(host_key) DESC, last_access_utc DESC
            """,
            (f"%{domain}%",),
        )
        if not rows:
            continue

        for name, value, encrypted_value in rows:
            if name in collected:
                continue
            plain_value = value or _decrypt_chromium_value(encrypted_value, master_key)
            if plain_value:
                collected[name] = plain_value

        if collected:
            profile_path = str(profile)
            break

    if not collected:
        raise CookieImportError(f"No {domain} cookies were found in {browser}")

    return ImportedCookieJar(
        browser=browser,
        cookie_header=_build_cookie_header(collected),
        cookie_count=len(collected),
        profile_path=profile_path,
    )


def import_firefox_cookies(domain: str) -> ImportedCookieJar:
    if not FIREFOX_PROFILES_DIR.exists():
        raise CookieImportError("Firefox profiles were not found on this machine")

    collected: dict[str, str] = {}
    profile_path = ""
    for profile in sorted(FIREFOX_PROFILES_DIR.iterdir()):
        if not profile.is_dir():
            continue
        db_path = profile / "cookies.sqlite"
        if not db_path.exists():
            continue

        rows = _query_sqlite_rows(
            db_path,
            """
            SELECT name, value
            FROM moz_cookies
            WHERE host LIKE ?
            ORDER BY LENGTH(host) DESC, lastAccessed DESC
            """,
            (f"%{domain}%",),
        )
        if not rows:
            continue

        for name, value in rows:
            if name not in collected and value:
                collected[name] = value

        if collected:
            profile_path = str(profile)
            break

    if not collected:
        raise CookieImportError(f"No {domain} cookies were found in Firefox")

    return ImportedCookieJar(
        browser="firefox",
        cookie_header=_build_cookie_header(collected),
        cookie_count=len(collected),
        profile_path=profile_path,
    )


def import_browser_cookies(browser: str, domain: str) -> ImportedCookieJar:
    browser = (browser or "").strip().lower()
    if browser in CHROMIUM_SOURCES:
        return import_chromium_cookies(browser, domain)
    if browser == "firefox":
        return import_firefox_cookies(domain)
    raise CookieImportError(f"Unsupported browser: {browser}")
