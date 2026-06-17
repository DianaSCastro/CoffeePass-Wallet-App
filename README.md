# LoyaltyChain Wallet — Backend Completo

Sistema de fidelidad con pases reales para Google Wallet y Apple Wallet.

---

## Estructura

```
loyalty-wallet/
├── app/
│   ├── main.py           # FastAPI — endpoints
│   ├── google_wallet.py  # JWT para Google Wallet
│   └── apple_wallet.py   # .pkpass para Apple Wallet
├── certs/                # Certificados (NO subir a git)
│   ├── google-service-account.json
│   ├── pass.crt
│   ├── pass.key
│   ├── wwdr.pem
│   └── apple_assets/     # icon.png, logo.png, etc.
├── templates/
│   └── index.html        # Frontend listo
├── .env.example
├── requirements.txt
└── README.md
```

---

## Setup — Google Wallet

### 1. Habilitar la API
1. Entra a [Google Cloud Console](https://console.cloud.google.com)
2. APIs & Services → Enable APIs → busca **"Google Wallet API"** → habilitar

### 2. Crear Service Account
1. IAM & Admin → Service Accounts → **+ Create Service Account**
2. Nombre: `loyaltychain-wallet`
3. Rol: `Service Account Token Creator` + `Wallet Object Issuer`
4. Keys → Add Key → **JSON** → descarga y guarda como `certs/google-service-account.json`

### 3. Google Pay & Wallet Console
1. Ve a [pay.google.com/business/console](https://pay.google.com/business/console)
2. Google Wallet API → **Issuers** → Create Issuer
3. Añade el email de tu Service Account como usuario
4. Copia tu **Issuer ID** (número largo)

### 4. Variables de entorno
```bash
cp .env.example .env
# Edita .env con tu ISSUER_ID y la ruta al JSON
GOOGLE_WALLET_ISSUER_ID=3388000000012345678
GOOGLE_SERVICE_ACCOUNT_FILE=certs/google-service-account.json
```

---

## Setup — Apple Wallet

### Requisitos
- Cuenta de Apple Developer ($99/año)
- Mac con Xcode (para generar certificados)

### 1. Registrar Pass Type ID
1. [developer.apple.com](https://developer.apple.com) → Account → Certificates, IDs & Profiles
2. Identifiers → **+** → Pass Type IDs
3. Nombre: `pass.io.loyaltychain.member` (usa tu dominio)

### 2. Crear certificado de firma
1. Genera un CSR en Keychain Access (Mac) → Certificate Assistant → Request a Certificate
2. En Apple Developer, selecciona tu Pass Type ID → Edit → Create Certificate → sube el CSR
3. Descarga el `.cer` → doble clic para instalar en Keychain
4. Exporta como `.p12` desde Keychain (guarda la contraseña)

### 3. Extraer clave y certificado
```bash
# Sin contraseña (para el servidor)
openssl pkcs12 -in cert.p12 -nocerts -nodes   -out certs/pass.key
openssl pkcs12 -in cert.p12 -clcerts -nokeys  -out certs/pass.crt

# WWDR (Autoridad raíz de Apple)
curl -o certs/wwdr.pem https://www.apple.com/certificateauthority/AppleWWDRCAG4.cer
```

### 4. Imágenes requeridas
Crea `certs/apple_assets/` con estas imágenes PNG:
```
icon.png        29x29 px
icon@2x.png     58x58 px
logo.png        160x50 px
logo@2x.png     320x100 px
strip.png       320x84 px   (banner superior del pase)
strip@2x.png    640x168 px
```

### 5. Variables de entorno
```bash
APPLE_PASS_TYPE_ID=pass.io.loyaltychain.member
APPLE_TEAM_ID=ABCDE12345          # Tu Team ID de Apple Developer
APPLE_PASS_CERT=certs/pass.crt
APPLE_PASS_KEY=certs/pass.key
APPLE_WWDR_CERT=certs/wwdr.pem
```

---

## Instalación y ejecución

```bash
# Clonar / copiar el proyecto
cd loyalty-wallet

# Entorno virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Dependencias
pip install -r requirements.txt

# Variables de entorno
cp .env.example .env
# Edita .env con tus credenciales

# Arrancar servidor
uvicorn app.main:app --reload --port 8000
```

Abre `templates/index.html` en el navegador (o sírvelo estáticamente).

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/wallet/google/add-url` | Devuelve URL para Save to Google Wallet |
| POST | `/wallet/google/redirect` | Redirige directamente a Google Wallet |
| POST | `/wallet/apple/pass` | Descarga `.pkpass` para Apple Wallet |
| GET  | `/health` | Estado del servicio |

### Ejemplo de request
```json
POST /wallet/google/add-url
{
  "member_id": "4A2F-E9B1-MX",
  "name": "Carlos Mendoza",
  "points": 3840,
  "level": "Gold",
  "wallet_address": "0x4a2fC3d8e1B7a9F2..."
}
```

### Ejemplo de respuesta
```json
{
  "url": "https://pay.google.com/gp/v/save/eyJhbGci...",
  "token": "eyJhbGci..."
}
```

---

## Flujo en producción

```
Usuario toca "Añadir a Google Wallet"
  → Frontend POST /wallet/google/add-url
  → Backend genera JWT firmado con Service Account
  → Frontend abre window.open(url)
  → Google verifica el JWT y muestra pantalla "Save to Wallet"
  → Usuario acepta → el pase aparece en Google Wallet
```

```
Usuario toca "Añadir a Apple Wallet" (desde iPhone/Safari)
  → Frontend POST /wallet/apple/pass
  → Backend genera y firma el .pkpass
  → Safari detecta el Content-Type y lanza "Add to Apple Wallet"
  → Usuario acepta → el pase aparece en Wallet
```

---

## Actualizar puntos en tiempo real

Cuando el usuario gana o canjea puntos, usa la API de Google para actualizar:

```python
# google_wallet.py — agregar esta función
def update_loyalty_object(member_id: str, new_points: int):
    import requests as req
    creds = _credentials()
    creds.refresh(google.auth.transport.requests.Request())
    object_id = f"{ISSUER_ID}.{member_id}"
    url = f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{object_id}"
    patch = {
        "loyaltyPoints": {"balance": {"string": f"{new_points:,} LYL"}, "label": "Puntos LYL"},
        "tierPoints": new_points
    }
    req.patch(url, headers={"Authorization": f"Bearer {creds.token}"}, json=patch).raise_for_status()
```

Para Apple, envía una notificación push a través de APNs y el pase se recarga automáticamente.

---

## Seguridad

- Nunca expongas `certs/` en el repositorio — agrega a `.gitignore`
- Usa variables de entorno en producción (Railway, Render, etc.)
- Rota las credenciales de Service Account cada 90 días
