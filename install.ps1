# PowerShell Installer for Agentic Software Factory
Write-Host "Starting Agentic Software Factory installation..." -ForegroundColor Cyan

if (Get-Command python -ErrorAction SilentlyContinue) {
    python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/ankur-paan/agentic-software-factory/main/install.py').read().decode())"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    python3 -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/ankur-paan/agentic-software-factory/main/install.py').read().decode())"
} else {
    Write-Error "Python 3 is required to scaffold the Agentic Software Factory."
}
