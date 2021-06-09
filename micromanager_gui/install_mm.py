import os
import shutil
import ssl
import urllib.request
from pathlib import Path
from subprocess import run

MAC_RELEASE = 20210527
WIN_RELEASE = 20210518

ssl._create_default_https_context = ssl._create_unverified_context


def progressBar(current, chunksize, total, barLength=40):
    percent = float(current * chunksize) * 100 / total
    arrow = "-" * int(percent / 100 * barLength - 1) + ">"
    spaces = " " * (barLength - len(arrow))
    if not os.getenv("CI"):
        print("Progress: [%s%s] %d %%" % (arrow, spaces, percent), end="\r")


def download_url(url, output_path):
    print(f"downloading {url} ...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    urllib.request.urlretrieve(url, filename=output_path, reporthook=progressBar)


def mac_main(release=MAC_RELEASE):
    url = "https://valelab4.ucsf.edu/~MM/nightlyBuilds/2.0.0-gamma/Mac/"
    fname = f"Micro-Manager-2.0.0-gamma1-{release}.dmg"
    download_url(f"{url}{fname}", fname)
    run(["hdiutil", "attach", "-nobrowse", fname], check=True)
    src = f"/Volumes/Micro-Manager/{fname[:-4]}"
    dst = Path(__file__).parent / f"{fname[:-4]}_mac"
    print("copied to", dst)
    shutil.copytree(src, dst)
    run(["hdiutil", "detach", "/Volumes/Micro-Manager"], check=True)
    os.unlink(fname)
    # fix gatekeeper ... requires password
    run(["sudo", "xattr", "-r", "-d", "com.apple.quarantine", str(dst)], check=True)
    # # fix path randomization
    os.rename(dst / "ImageJ.app", "ImageJ.app")
    os.rename("ImageJ.app", dst / "ImageJ.app")
    print(os.listdir(Path(__file__).parent))


def win_main(release=WIN_RELEASE):
    url = "https://valelab4.ucsf.edu/~MM/nightlyBuilds/2.0.0-gamma/Windows/"
    fname = f"MMSetup_64bit_2.0.0-gamma1_{release}.exe"
    download_url(f"{url}{fname}", fname)
    dst = Path(__file__).parent / f"Micro-Manager-2.0.0-gamma1-{release}_win"
    run(
        [fname, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={dst}"],
        check=True,
    )
    os.unlink(fname)


if __name__ == "__main__":
    if os.name == "nt":
        win_main()
    else:
        mac_main()
