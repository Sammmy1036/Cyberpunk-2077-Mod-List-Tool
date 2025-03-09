$cert = New-SelfSignedCertificate -Subject "My Application Name.exe" -CertStoreLocation "cert:\CurrentUser\My" -HashAlgorithm sha256 -Type CodeSigning

$pwd = ConvertTo-SecureString -String "YourPassword" -Force -AsPlainText

Export-PfxCertificate -Cert $cert -FilePath "MyApplicationName.pfx" -Password $pwd
