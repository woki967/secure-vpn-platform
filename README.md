# Automatyczne wdrażanie usług lokalnych z wykorzystaniem pełnych aspektów bezpieczeństwa (HTTPS + Proxy Auth)

## Autorzy

* Wojciech Wluka
* Mateusz Kobylski
* Mirosław Bidziński

# WireGuard VPN Reverse Proxy Platform

## Wprowadzenie

Platforma umożliwia bezpieczne publikowanie usług działających w prywatnej sieci WireGuard VPN bez konieczności ręcznej konfiguracji serwera, reverse proxy oraz certyfikatów SSL.

Cały proces wdrożenia i zarządzania usługami został zautomatyzowany przy użyciu:

* GitHub Actions
* Terraform
* Ansible
* Docker
* Nginx
* WireGuard (WG-Easy)
* Uptime Kuma
* Let's Encrypt

Po wdrożeniu użytkownik może publikować własne usługi działające lokalnie za pośrednictwem połączenia VPN.

---

# Wymagania

Przed rozpoczęciem instalacji należy przygotować:

* Konto GitHub
* Subskrypcję Microsoft Azure
* Ubuntu Server 24.04 (tworzony automatycznie przez Terraform)
* Domenę DNS (opcjonalnie można wykorzystać Azure FQDN)
* Klienta WireGuard
* Python 3.x

---

# Instalacja

## Krok 1 — Klonowanie repozytorium

Sklonuj repozytorium:

```bash
git clone https://github.com/<twoje-repo>.git

cd <twoje-repo>
```

---

## Krok 2 — Uruchomienie skryptu Azure Bootstrap

Uruchom skrypt odpowiedzialny za przygotowanie integracji pomiędzy Azure oraz GitHub Actions.

Przykład:

```bash
python bootstrap_azure.py
```

Skrypt automatycznie:

* tworzy aplikację Azure AD
* tworzy Service Principal
* tworzy Federated Credential dla GitHub OIDC
* nadaje wymagane uprawnienia do subskrypcji Azure
* generuje dane wymagane przez GitHub Actions

Po zakończeniu działania zostaną wyświetlone:

```text
AZURE_CLIENT_ID=xxxxxxxx
AZURE_TENANT_ID=xxxxxxxx
AZURE_SUBSCRIPTION_ID=xxxxxxxx
```

Zapisz te wartości.

---

## Krok 3 — Wygenerowanie kluczy SSH

Jeżeli nie posiadasz kluczy SSH:

```bash
ssh-keygen -t ed25519 -C "github-actions"
```

Powstaną pliki:

```text
~/.ssh/id_ed25519
~/.ssh/id_ed25519.pub
```

---

## Krok 4 — Konfiguracja GitHub Secrets

Przejdź do:

```text
Repository → Settings → Secrets and variables → Actions
```

Dodaj następujące sekrety.

### Azure

| Secret                |
| --------------------- |
| AZURE_CLIENT_ID       |
| AZURE_TENANT_ID       |
| AZURE_SUBSCRIPTION_ID |

### SSH

| Secret          |
| --------------- |
| SSH_PRIVATE_KEY |
| SSH_PUBLIC_KEY  |

### WireGuard

| Secret            |
| ----------------- |
| WG_ADMIN_USER     |
| WG_ADMIN_PASSWORD |

### Reverse Proxy

| Secret                    |
| ------------------------- |
| NGINX_BASIC_AUTH_USER     |
| NGINX_BASIC_AUTH_PASSWORD |

### Let's Encrypt

| Secret            |
| ----------------- |
| LETSENCRYPT_EMAIL |

---

# Pierwsze wdrożenie

## Krok 5 — Uruchomienie Bootstrap

Przejdź do:

```text
GitHub Actions → Bootstrap VM → Run workflow
```

Uzupełnij pola:

### resource_group_name

Nazwa grupy zasobów Azure.

Przykład:

```text
vpn-rg
```

### vm_name

Nazwa maszyny wirtualnej.

Przykład:

```text
vpn-server
```

### wg_domain

Domena WireGuard.

Przykład:

```text
vpn.example.com
```

Jeżeli chcesz użyć Azure FQDN pozostaw pole puste.

### kuma_domain

Domena Uptime Kuma.

Przykład:

```text
status.example.com
```

Pozostaw puste jeżeli nie chcesz korzystać z osobnej domeny.

### docker_subnet

Przykład:

```text
172.31.250.0/24
```

---

## Tryby wdrożenia

### Single Domain

```text
wg_domain = vpn.example.com
kuma_domain = (puste)
```

lub

```text
wg_domain = (puste)
kuma_domain = (puste)
```

System zostanie wdrożony w trybie:

```text
single
```

---

### Dual Domain

```text
wg_domain = vpn.example.com
kuma_domain = status.example.com
```

System zostanie wdrożony w trybie:

```text
dual
```

---

## Co wykonuje Bootstrap

Workflow automatycznie:

* Tworzy Resource Group
* Tworzy sieć Azure
* Tworzy subnet Azure
* Tworzy Public IP
* Tworzy Ubuntu Server 24.04
* Instaluje Docker
* Instaluje WireGuard (WG-Easy)
* Instaluje Nginx
* Instaluje Uptime Kuma
* Konfiguruje reverse proxy
* Tworzy certyfikaty Let's Encrypt
* Konfiguruje zabezpieczenia systemu
* Tworzy środowisko do publikacji usług

---

# Konfiguracja WireGuard

Po zakończeniu Bootstrap:

1. Otwórz panel WG-Easy.
2. Utwórz klienta VPN.
3. Pobierz konfigurację WireGuard.
4. Zaimportuj konfigurację do klienta WireGuard.
5. Nawiąż połączenie VPN pomiędzy urządzeniem lokalnym a serwerem.

Dopiero po zestawieniu tunelu VPN możliwe jest publikowanie usług.

---

# Dodawanie usług

Przejdź do:

```text
GitHub Actions → Add Service
```

Podaj:

| Parametr     | Opis                                  |
| ------------ | ------------------------------------- |
| service_name | Nazwa usługi                          |
| vpn_ip       | Adres IP urządzenia w sieci WireGuard |
| local_port   | Port lokalnej aplikacji               |
| domain       | Domena usługi                         |
| public_port  | Publiczny port (opcjonalnie)          |
| proxy_auth   | yes / no                              |

Przykład:

```text
service_name=homeassistant
vpn_ip=10.8.0.10
local_port=8123
domain=home.example.com
proxy_auth=yes
```

---

# Zarządzanie usługami

Dostępne workflow:

### Bootstrap VM

Jednorazowe wdrożenie nowej infrastruktury.

### Add Service

Dodawanie nowych usług.

### Update Service

Aktualizacja istniejącej usługi.

### Delete Service

Usuwanie usługi.

### Update Domains

Zmiana konfiguracji domen oraz przełączanie pomiędzy trybem Single Domain i Dual Domain.

### Update Auth

Zmiana danych logowania do reverse proxy.

---

# Bezpieczeństwo

* Dane dostępowe przechowywane są w GitHub Secrets.
* Certyfikaty SSL generowane są automatycznie przez Let's Encrypt.
* Reverse proxy może zostać zabezpieczone Basic Auth.
* WireGuard wykorzystuje prywatną sieć VPN.
* Jawne hasło używane podczas pierwszego uruchomienia WG-Easy jest automatycznie usuwane przez rolę Ansible Security po zakończeniu procesu wdrożenia.

---

# Architektura

```text
Internet
    │
    ▼
Nginx Reverse Proxy
    │
    ├── WG-Easy
    ├── Uptime Kuma
    └── Usługi użytkownika
            │
            ▼
      WireGuard VPN
            │
            ▼
      Urządzenie lokalne
```
