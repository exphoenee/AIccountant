# AIccountant telepítő (Windows PowerShell 5.1+ / PowerShell 7): mappák, függőség-ellenőrzés, .env létrehozása API-kulcsokkal.
#
# Használat:
#   .\install.ps1                      # interaktív: rákérdez a Billingo és a Számlázz.hu API-kulcsra (Enter = kihagyás)
#   $env:BILLING_API_KEY='...'; $env:SZAMLAZZ_API_KEY='...'; .\install.ps1 -NemInteraktiv
#
# A kulcsokat nem írja ki a képernyőre. Meglévő .env esetén a kitöltött értékeket megtartja, csak a hiányzókra kérdez rá.
# Nincs hálózati letöltés, nincs csomagtelepítés: a scriptek csak a Python standard könyvtárát használják.
param([switch]$NemInteraktiv)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$utf8 = New-Object System.Text.UTF8Encoding($false)

Write-Host '== AIccountant telepítés =='

# 1) Python 3.10+
$py = $null
foreach ($c in 'python', 'python3', 'py') {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) {
        & $cmd.Source -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { $py = $cmd.Source; break }
    }
}
if (-not $py) {
    Write-Host 'HIBA: Python 3.10 vagy újabb szükséges. Telepítés: https://www.python.org/downloads/ (vagy: winget install Python.Python.3.13)' -ForegroundColor Red
    exit 1
}
Write-Host ('OK   Python: ' + (& $py --version 2>&1))

# 2) pdftotext
$pdft = Get-Command pdftotext -ErrorAction SilentlyContinue
if (-not $pdft) {
    foreach ($p in 'C:\Program Files\Git\mingw64\bin\pdftotext.exe', 'C:\Program Files\Git\usr\bin\pdftotext.exe') { if (Test-Path $p) { $pdft = $p; break } }
}
if ($pdft) { Write-Host 'OK   pdftotext: megvan' }
else { Write-Host 'FIGYELEM: a pdftotext nincs telepítve; PDF-ek feldolgozásához kell. A Git for Windows tartalmazza (https://git-scm.com), vagy: winget install oschwartz10612.Poppler' -ForegroundColor Yellow }

# 3) mappák
$mappak = 'input\vallalkozas-adatok', 'input\nav-egyenleg', 'input\adonaptar', 'input\konyvelo', 'input\kiadasok', 'input\bevetelek', 'input\torveny', 'input\pdf',
          'data', 'archive', 'tax-reports', 'audits', 'docs', 'config', 'torvenytar', '.claude\memory'
foreach ($d in $mappak) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
foreach ($d in 'input\vallalkozas-adatok', 'input\nav-egyenleg', 'input\adonaptar', 'input\konyvelo', 'input\kiadasok', 'input\bevetelek', 'input\torveny', 'input\pdf', 'archive', 'tax-reports') {
    $k = Join-Path $d '.gitkeep'
    if (-not (Test-Path $k)) { New-Item -ItemType File -Path $k | Out-Null }
}
Write-Host 'OK   mappák létrehozva'

# 4) .gitignore
if (-not (Test-Path .gitignore)) { New-Item -ItemType File -Path .gitignore | Out-Null }
$gi = Get-Content .gitignore -ErrorAction SilentlyContinue
foreach ($e in '.env', 'data/', 'archive/', 'input/', 'tax-reports/', 'audits/', 'config/vallalkozas.json', '.claude/memory/vallalkozasi-profil.md', '.claude/memory/adonaptar-*.md', 'todo.md', 'level-*.md', '__pycache__/', '*.pyc') {
    if ($gi -notcontains $e) { Add-Content -Path .gitignore -Value $e -Encoding utf8 }
}
Write-Host 'OK   .gitignore ellenőrizve'

# 4/b) config/vallalkozas.json a sablonból (a null mezőket a vállalkozónak kell kitöltenie; a fájl nincs verziókezelve)
if (-not (Test-Path 'configallalkozas.json') -and (Test-Path 'configallalkozas.example.json')) {
    Copy-Item 'configallalkozas.example.json' 'configallalkozas.json'
    Write-Host 'OK   configallalkozas.json létrehozva a sablonból (a null mezőket töltsd ki; lásd usage.md)'
}

# 5) .env
function Get-EnvErtek([string]$nev) {
    if (Test-Path .env) {
        foreach ($sor in Get-Content .env -Encoding utf8) {
            if ($sor -match "^$nev=(.*)$") { return $Matches[1].Trim().Trim('"').Trim("'") }
        }
    }
    return ''
}
function Read-Titok([string]$kerdes) {
    $ss = Read-Host -Prompt $kerdes -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($ss)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}
$billing = Get-EnvErtek 'BILLING_API_KEY'
$szamlazz = Get-EnvErtek 'SZAMLAZZ_API_KEY'
$sorozat = Get-EnvErtek 'SZAMLAZZ_SOROZAT'

if ($NemInteraktiv) {
    if (-not $billing) { $billing = [string]$env:BILLING_API_KEY }
    if (-not $szamlazz) { $szamlazz = [string]$env:SZAMLAZZ_API_KEY }
    if (-not $sorozat) { $sorozat = [string]$env:SZAMLAZZ_SOROZAT }
}
else {
    Write-Host ''
    Write-Host 'API-kulcsok (Enter = kihagyás; kulcs nélkül az adott forrás adatait a rendszer csendben átugorja):'
    if (-not $billing) { $billing = Read-Titok '  Billingo API-kulcs (csak olvasási jogosultság; Billingo > Beállítások > API)' } else { Write-Host '  Billingo API-kulcs: már megvan a .env-ben' }
    if (-not $szamlazz) { $szamlazz = Read-Titok '  Számlázz.hu Számla Agent kulcs (Számlázz.hu > Beállítások > Számla Agent)' } else { Write-Host '  Számlázz.hu kulcs: már megvan a .env-ben' }
    if ($szamlazz -and -not $sorozat) { $sorozat = Read-Host -Prompt '  Számlázz.hu számlaszám-minta a lekéréshez, pl. ABC-2026-{n} (Enter = később)' }
}

$tartalom = "# AIccountant titkok: NEM verziózott, ne oszd meg.`nBILLING_API_KEY=$billing`nSZAMLAZZ_API_KEY=$szamlazz`nSZAMLAZZ_SOROZAT=$sorozat`n"
[System.IO.File]::WriteAllText((Join-Path $PWD '.env'), $tartalom, $utf8)
# a .env csak a jelenlegi felhasználó számára olvasható
try { & icacls .env /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null } catch { }
if ($billing) { Write-Host 'OK   .env: BILLING_API_KEY megadva' } else { Write-Host 'INFO .env: BILLING_API_KEY üres (a Billingo-adatok kimaradnak)' }
if ($szamlazz) { Write-Host 'OK   .env: SZAMLAZZ_API_KEY megadva' } else { Write-Host 'INFO .env: SZAMLAZZ_API_KEY üres (a Számlázz.hu-adatok kimaradnak)' }

# 6) önellenőrzés
$teszt = '.claude\skills\adoszamitas\scripts\teszt_nav_peldak.py'
if (Test-Path $teszt) {
    & $py -I $teszt *> $null
    if ($LASTEXITCODE -eq 0) { Write-Host 'OK   számítás-önteszt (NAV-példák): megfelelt' }
    else { Write-Host "FIGYELEM: a számítás-önteszt nem futott le; lásd: python -I $teszt" -ForegroundColor Yellow }
}

Write-Host @'

Kész. Következő lépések (részletesen: usage.md):
  1. Másold a vállalkozás iratait az input\vallalkozas-adatok\ mappába, majd kérd a Claude-tól a vallalkozas-dokumentumok skillt (ez az ELSŐ lépés).
  2. Utána: input\konyvelo, input\kiadasok, input\bevetelek, input\nav-egyenleg, input\adonaptar mappák.
  3. Adóellenőrzés: python -I .claude\skills\adoellenorzes\scripts\adoellenorzes.py (csak a vállalkozói profil elkészülte után fut).
'@
