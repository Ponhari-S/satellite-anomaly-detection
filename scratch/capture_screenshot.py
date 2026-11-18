import subprocess
import os

out_png = os.path.abspath("scratch/dashboard_1920x1080.png")
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
html_path = os.path.abspath("frontend/dist/index.html").replace("\\", "/")
url = f"file:///{html_path}"

cmd = [
    chrome_path,
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--allow-file-access-from-files",
    f"--screenshot={out_png}",
    "--window-size=1920,1080",
    "--hide-scrollbars",
    "--virtual-time-budget=3000",
    url
]

print("Capturing screenshot of:", url)
res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
print("Return code:", res.returncode)
print("Stdout:", res.stdout)
print("Stderr:", res.stderr)
print("File exists:", os.path.exists(out_png))
if os.path.exists(out_png):
    print("Size bytes:", os.path.getsize(out_png))
