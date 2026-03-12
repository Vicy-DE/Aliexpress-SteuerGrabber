"""Firefox profile detection and cookie extraction.

Locates the default Firefox profile on Windows (standard and MSIX installs),
copies the cookies database to a temp file to avoid locking conflicts, and
converts cookies to Playwright-compatible format.
"""

import configparser
import shutil
import sqlite3
import tempfile
from pathlib import Path
import os


def find_firefox_profile():
    """Find the default Firefox profile directory on Windows.

    Returns:
        Path to the Firefox profile directory.

    Raises:
        FileNotFoundError: If no Firefox profile is found.
    """
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")

    candidates = [
        Path(appdata) / "Mozilla" / "Firefox" / "profiles.ini",
    ]

    packages_dir = Path(localappdata) / "Packages"
    if packages_dir.exists():
        for pkg in packages_dir.iterdir():
            if pkg.name.startswith("Mozilla.Firefox"):
                msix_ini = (
                    pkg / "LocalCache" / "Roaming"
                    / "Mozilla" / "Firefox" / "profiles.ini"
                )
                candidates.insert(0, msix_ini)

    profiles_ini = None
    for candidate in candidates:
        if candidate.exists():
            profiles_ini = candidate
            break

    if profiles_ini is None:
        raise FileNotFoundError(
            "Firefox profiles.ini not found. Searched:\n"
            + "\n".join(f"  - {c}" for c in candidates)
            + "\nIs Firefox installed?"
        )

    firefox_dir = profiles_ini.parent
    print(f"Found profiles.ini: {profiles_ini}")

    config = configparser.ConfigParser()
    config.read(str(profiles_ini))

    # Priority 1: InstallXXX section's Default= key
    profile_path = None
    for section in config.sections():
        if section.startswith("Install"):
            path = config.get(section, "Default", fallback="")
            if path:
                candidate = firefox_dir / path
                if candidate.exists() and (candidate / "cookies.sqlite").exists():
                    profile_path = candidate
                    break

    # Priority 2: Profile sections — prefer one with cookies.sqlite
    if profile_path is None:
        fallback = None
        for section in config.sections():
            if not section.startswith("Profile"):
                continue
            is_relative = config.get(section, "IsRelative", fallback="1") == "1"
            path = config.get(section, "Path", fallback="")

            if path:
                candidate = (firefox_dir / path) if is_relative else Path(path)
                if candidate.exists() and (candidate / "cookies.sqlite").exists():
                    profile_path = candidate
                    break
                if fallback is None and candidate.exists():
                    fallback = candidate

        if profile_path is None:
            profile_path = fallback

    if profile_path is None or not profile_path.exists():
        raise FileNotFoundError(
            "Could not find a Firefox profile directory. "
            "Make sure Firefox is installed and has been used at least once."
        )

    print(f"Found Firefox profile: {profile_path}")
    return profile_path


def extract_firefox_cookies(profile_path, domain_filter=".aliexpress.com"):
    """Extract cookies from a running Firefox instance's profile.

    Copies the cookies database to a temp file to avoid locking conflicts
    with the running Firefox process.

    Args:
        profile_path: Path to the Firefox profile directory.
        domain_filter: Domain to filter cookies for.

    Returns:
        List of cookie dicts compatible with Playwright's add_cookies().
    """
    cookies_db = profile_path / "cookies.sqlite"
    if not cookies_db.exists():
        raise FileNotFoundError(f"cookies.sqlite not found in {profile_path}")

    tmp_dir = tempfile.mkdtemp(prefix="firefox_cookies_")
    tmp_db = Path(tmp_dir) / "cookies.sqlite"
    shutil.copy2(str(cookies_db), str(tmp_db))

    for suffix in ["-wal", "-shm"]:
        wal_file = profile_path / f"cookies.sqlite{suffix}"
        if wal_file.exists():
            shutil.copy2(
                str(wal_file),
                str(Path(tmp_dir) / f"cookies.sqlite{suffix}"),
            )

    cookies = []
    try:
        conn = sqlite3.connect(str(tmp_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT host, name, value, path, expiry, isSecure, "
            "isHttpOnly, sameSite "
            "FROM moz_cookies WHERE host LIKE ?",
            (f"%{domain_filter}%",),
        )

        sameSite_map = {0: "None", 1: "Lax", 2: "Strict"}

        for row in cursor.fetchall():
            host, name, value, path, expiry, is_secure, is_http_only, same_site = row
            cookie = {
                "name": name,
                "value": value,
                "domain": host,
                "path": path or "/",
                "secure": bool(is_secure),
                "httpOnly": bool(is_http_only),
                "sameSite": sameSite_map.get(same_site, "None"),
            }
            if expiry and expiry > 0:
                if expiry > 1e12:
                    expiry = int(expiry / 1000)
                cookie["expires"] = expiry
            else:
                cookie["expires"] = -1
            cookies.append(cookie)

        conn.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"  Extracted {len(cookies)} AliExpress cookies from Firefox.")
    if not cookies:
        print("  WARNING: No AliExpress cookies found!")
        print("  Make sure you are logged into AliExpress in Firefox.")
    return cookies
