<# This is the installation script of VIAN for windows, 
essentially it downloads VLC 64-bit, installs miniconda and 
sets up the VIAN environment in it. 
#>

Set-Location "${0%/*}"
Get-Location
$root = Get-Location
$minicondapath  = "$root\python\"
Write-Output $minicondapath

# Create a temporary directory where we put all downloaded resources
mkdir "$root\install_temporary\"
Set-Location install_temporary

# # Install VLC 64-bit
# Invoke-WebRequest https://mirror.init7.net/videolan/vlc/3.0.6/win64/vlc-3.0.6-win64.exe -OutFile vlc64_installer.exe
# .\vlc64_installer.exe | Out-Wait
# Write-Host "VLC Installed" 

# Install Miniconda
Invoke-WebRequest https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe -OutFile miniconda.exe
.\miniconda.exe /InstallationType=JustMe /RegisterPython=0 /S /D=$minicondapath

# Create Conda Env





