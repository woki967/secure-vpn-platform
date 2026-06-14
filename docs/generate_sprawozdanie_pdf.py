#!/usr/bin/env python3
"""Generate repository documentation PDF (HTML intermediate + LibreOffice)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent
HTML_PATH = DOCS_DIR / "sprawozdanie-repozytorium.html"
PDF_PATH = DOCS_DIR / "sprawozdanie-repozytorium.pdf"

HTML = r"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <title>Sprawozdanie — repozytorium validationtest</title>
  <style>
    @page { margin: 2cm; }
    body {
      font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
      font-size: 11pt;
      line-height: 1.45;
      color: #1a1a1a;
      max-width: 900px;
      margin: 0 auto;
      padding: 24px;
    }
    h1 { font-size: 22pt; border-bottom: 2px solid #2563eb; padding-bottom: 8px; }
    h2 { font-size: 15pt; margin-top: 28px; color: #1e40af; page-break-after: avoid; }
    h3 { font-size: 12pt; margin-top: 18px; color: #334155; page-break-after: avoid; }
    h4 { font-size: 11pt; margin-top: 14px; color: #475569; }
    p, li { text-align: justify; }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0 18px;
      font-size: 10pt;
    }
    th, td {
      border: 1px solid #cbd5e1;
      padding: 6px 8px;
      vertical-align: top;
    }
    th { background: #eff6ff; text-align: left; }
    code, pre {
      font-family: "Liberation Mono", monospace;
      font-size: 9pt;
      background: #f8fafc;
    }
    pre {
      border: 1px solid #e2e8f0;
      padding: 10px;
      overflow-x: auto;
      white-space: pre-wrap;
    }
    .meta { color: #64748b; font-size: 10pt; margin-bottom: 24px; }
    .toc { background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px 20px; }
    .toc ol { margin: 0; padding-left: 20px; }
    .toc li { margin: 4px 0; }
    .diagram {
      background: #f1f5f9;
      border-left: 4px solid #2563eb;
      padding: 12px 16px;
      font-family: monospace;
      font-size: 9pt;
      white-space: pre-wrap;
    }
    .page-break { page-break-before: always; }
    ul { margin-top: 6px; }
  </style>
</head>
<body>

<h1>Sprawozdanie techniczne<br>Repozytorium <em>validationtest</em></h1>
<p class="meta">
  Dokument opisuje architekturę, pliki, przepływ danych i sposób działania
  infrastruktury VPN/proxy na Azure.<br>
  Data wygenerowania: 14 czerwca 2026
</p>

<div class="toc">
  <strong>Spis treści</strong>
  <ol>
    <li>Cel projektu i architektura wysokiego poziomu</li>
    <li>Życie projektu — od zera do działającej usługi</li>
    <li>Pliki w katalogu głównym</li>
    <li>Terraform — infrastruktura Azure</li>
    <li>Skrypty pomocnicze (<code>scripts/</code>)</li>
    <li>GitHub Actions — workflowy CI/CD</li>
    <li>Ansible — playbooki i role</li>
    <li>Pliki tworzone na maszynie wirtualnej</li>
    <li>Tryby wdrożenia (single / dual)</li>
    <li>Sekrety i zmienne GitHub</li>
    <li>Mapa zależności — co z czego wynika</li>
  </ol>
</div>

<h2>1. Cel projektu i architektura wysokiego poziomu</h2>

<p>
  Repozytorium <strong>validationtest</strong> automatyzuje wdrożenie serwera VPN
  z reverse proxy w chmurze Microsoft Azure. Na jednej maszynie wirtualnej (VM)
  uruchamiane są kontenery Docker:
</p>
<ul>
  <li><strong>WG-Easy</strong> — serwer WireGuard (VPN), sieć klientów <code>10.8.0.0/24</code></li>
  <li><strong>Uptime Kuma</strong> — monitoring dostępności usług</li>
  <li><strong>nginx</strong> — reverse proxy z certyfikatami TLS (Let's Encrypt)</li>
  <li><strong>certbot</strong> — pomocniczy kontener do odnawiania certyfikatów</li>
</ul>

<p>
  Użytkownik może dodawać własne usługi (np. aplikację na IP klienta VPN
  <code>10.8.0.2:8080</code>), które nginx wystawia na zewnątrz — albo pod własną
  domeną (HTTPS na porcie 443), albo pod publicznym portem VM (np. <code>9090</code>).
</p>

<p>Projekt składa się z trzech warstw:</p>
<table>
  <tr><th>Warstwa</th><th>Technologia</th><th>Odpowiedzialność</th></tr>
  <tr>
    <td>Infrastruktura</td>
    <td>Terraform + Azure</td>
    <td>VM, sieć, firewall (NSG), publiczny IP, FQDN Azure</td>
  </tr>
  <tr>
    <td>Konfiguracja VM</td>
    <td>Ansible</td>
    <td>Docker, nginx, certyfikaty, routing WireGuard, pliki usług</td>
  </tr>
  <tr>
    <td>Orkiestracja</td>
    <td>GitHub Actions</td>
    <td>Bootstrap, deploy, dodawanie/edycja/usuwanie usług, sync NSG</td>
  </tr>
</table>

<div class="diagram">┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ boostrap_       │     │ GitHub Actions   │     │ Azure VM (/opt/repo) │
│ terraform.py    │────▶│ (9 workflowów)   │────▶│ Docker + nginx       │
│ (lokalnie)      │     │ + Terraform      │     │ services/*.yml       │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                         │                         │
        ▼                         ▼                         ▼
 terraform/backend.tf      NSG + public_ip           .bootstrap.env
 output/ (klucze SSH)      OIDC do Azure            docker-compose.yml</div>

<h2>2. Życie projektu — od zera do działającej usługi</h2>

<h3>Krok 1 — Bootstrap lokalny (jednorazowo)</h3>
<p>Na komputerze dewelopera uruchamiasz:</p>
<pre>python bootstrap.py</pre>
<p>Skrypt (<code>boostrap_terraform.py</code>) wykonuje:</p>
<ol>
  <li>Wykrywa repozytorium GitHub z <code>git remote</code></li>
  <li>Sprawdza logowanie do Azure (<code>az login</code>)</li>
  <li>Tworzy (lub używa) grupę zasobów <code>rg-terraform-state</code> i konto Storage na stan Terraform</li>
  <li>Generuje <code>terraform/backend.tf</code> — konfigurację zdalnego stanu</li>
  <li>Generuje parę kluczy SSH w <code>output/id_ed25519</code></li>
  <li>Tworzy aplikację Azure AD <code>{nazwa-repo}-github-actions</code> z federacją OIDC dla GitHub Actions</li>
  <li>Wypisuje wartości do skopiowania jako GitHub Variables i Secrets</li>
  <li>Opcjonalnie commituje i pushuje <code>backend.tf</code></li>
</ol>

<h3>Krok 2 — Bootstrap VM (workflow GitHub)</h3>
<p>Workflow <strong>Bootstrap VM</strong> (<code>bootstrap-vm.yml</code>):</p>
<ol>
  <li><code>terraform apply</code> — tworzy VM, sieć, NSG</li>
  <li>Czeka na propagację DNS (do 10 min), jeśli podano własne domeny</li>
  <li>Łączy się SSH jako <code>azureuser</code></li>
  <li>Klonuje repo do <code>/opt/{nazwa-repo}</code></li>
  <li>Zapisuje <code>.bootstrap.env</code> (domeny, tryb, podsieci Docker)</li>
  <li>Uruchamia <code>ansible-playbook bootstrap.yml</code></li>
</ol>

<h3>Krok 3 — Deploy przy pushu</h3>
<p>Push na gałąź <code>main</code> uruchamia <code>deploy.yml</code> (z wyjątkiem samego <code>backend.tf</code>).
Na VM: <code>git pull</code> + <code>ansible/deploy.yml</code>.</p>

<h3>Krok 4 — Zarządzanie usługami</h3>
<p>Workflowy ręczne: dodaj / edytuj / usuń usługę → plik YAML na VM → synchronizacja NSG → Ansible.</p>

<h2 class="page-break">3. Pliki w katalogu głównym</h2>

<table>
  <tr><th>Plik</th><th>Opis</th></tr>
  <tr>
    <td><code>boostrap_terraform.py</code></td>
    <td>
      Główny skrypt bootstrapu (nazwa z literówką — historycznie).
      ~700 linii. Działa na Linux i Windows. Tworzy backend Terraform,
      klucze SSH, aplikację OIDC Azure. Funkcje pomocnicze:
      <code>build_command()</code> (Windows: <code>cmd /c az.cmd</code>),
      <code>push_backend_tf()</code> (commit tylko gdy plik się zmienił).
    </td>
  </tr>
  <tr>
    <td><code>bootstrap.py</code><br><code>bootstrap_terraform.py</code></td>
    <td>Cienkie aliasy — wywołują <code>main()</code> z <code>boostrap_terraform.py</code>.</td>
  </tr>
  <tr>
    <td><code>.env.template</code></td>
    <td>
      Szablon zmiennych środowiskowych WG-Easy. Przy bootstrapie VM
      workflow podstawia <code>WG_ADMIN_USER</code>, <code>WG_ADMIN_PASSWORD</code>,
      <code>WG_DOMAIN</code>, <code>DOCKER_SUBNET</code> przez <code>envsubst</code>
      i zapisuje jako <code>.env</code> na VM.
    </td>
  </tr>
  <tr>
    <td><code>.gitignore</code></td>
    <td>Ignoruje <code>output/</code> (klucze SSH, podsumowanie bootstrapu), <code>__pycache__/</code>.</td>
  </tr>
  <tr>
    <td><code>README.md</code></td>
    <td>Placeholder — tylko tytuł repozytorium.</td>
  </tr>
</table>

<h3>Katalog <code>output/</code> (lokalny, gitignored)</h3>
<table>
  <tr><th>Plik</th><th>Opis</th></tr>
  <tr><td><code>id_ed25519</code></td><td>Klucz prywatny SSH → GitHub Secret <code>SSH_PRIVATE_KEY</code></td></tr>
  <tr><td><code>id_ed25519.pub</code></td><td>Klucz publiczny → GitHub Variable <code>SSH_PUBLIC_KEY</code></td></tr>
  <tr><td><code>federation.json</code></td><td>Konfiguracja federacji OIDC Azure AD dla GitHub Actions</td></tr>
  <tr><td><code>bootstrap-summary.txt</code></td><td>Podsumowanie tekstowe: Client ID, Tenant ID, ścieżki plików</td></tr>
</table>

<h2>4. Terraform — infrastruktura Azure</h2>

<p>Katalog <code>terraform/</code> definiuje zasoby Azure dla jednej maszyny VPN/proxy.</p>

<h3>Pliki Terraform</h3>
<table>
  <tr><th>Plik</th><th>Zawartość</th></tr>
  <tr>
    <td><code>provider.tf</code></td>
    <td>Wymaga Terraform ≥ 1.6, provider <code>azurerm</code> w wersji ~4.0.</td>
  </tr>
  <tr>
    <td><code>backend.tf</code></td>
    <td>
      Zdalny stan w Azure Storage (generowany przez skrypt bootstrap).
      Klucz stanu: <code>{nazwa-repo}.tfstate</code>.
    </td>
  </tr>
  <tr>
    <td><code>variables.tf</code></td>
    <td>Wejścia Terraform (tabela poniżej).</td>
  </tr>
  <tr>
    <td><code>locals.tf</code></td>
    <td>
      Porty zarezerwowane: 22, 80, 443, 8443, 51820. Filtruje
      <code>public_ports</code> i nadaje priorytety regułom NSG od 140 w górę.
    </td>
  </tr>
  <tr>
    <td><code>network.tf</code></td>
    <td>
      Resource Group, VNet <code>10.0.0.0/16</code>, subnet <code>10.0.1.0/24</code>,
      NSG z regułami: SSH(100), HTTP(110), HTTPS(120), 8443(125, tryb single),
      WireGuard UDP 51820(130), dynamiczne porty usług(140+).
    </td>
  </tr>
  <tr>
    <td><code>vm.tf</code></td>
    <td>
      Publiczny IP (Static, Standard) z opcjonalnym FQDN Azure,
      NIC, VM Ubuntu 24.04, użytkownik <code>azureuser</code>, logowanie kluczem SSH.
    </td>
  </tr>
  <tr>
    <td><code>outputs.tf</code></td>
    <td>Wyjścia: <code>public_ip</code>, <code>azure_fqdn</code>, <code>vm_name</code>, <code>azure_subnet</code>, <code>resource_group_name</code>.</td>
  </tr>
</table>

<h3>Zmienne wejściowe Terraform</h3>
<table>
  <tr><th>Zmienna</th><th>Typ</th><th>Domyślnie</th><th>Znaczenie</th></tr>
  <tr><td>resource_group_name</td><td>string</td><td>—</td><td>Nazwa grupy zasobów Azure (wymagana)</td></tr>
  <tr><td>location</td><td>string</td><td>polandcentral</td><td>Region Azure</td></tr>
  <tr><td>vm_name</td><td>string</td><td>""</td><td>Nazwa maszyny wirtualnej</td></tr>
  <tr><td>vm_size</td><td>string</td><td>Standard_B2ats_v2</td><td>Rozmiar VM</td></tr>
  <tr><td>ssh_public_key</td><td>string</td><td>""</td><td>Klucz publiczny SSH administratora</td></tr>
  <tr><td>single_domain_mode</td><td>bool</td><td>false</td><td>true = otwiera port 8443 w NSG (Kuma na tej samej domenie co WG)</td></tr>
  <tr><td>public_ports</td><td>list(number)</td><td>[]</td><td>Dodatkowe porty TCP dla usług bez własnej domeny</td></tr>
</table>

<h3>Reguły NSG — podsumowanie</h3>
<table>
  <tr><th>Priorytet</th><th>Port</th><th>Protokół</th><th>Kiedy aktywna</th></tr>
  <tr><td>100</td><td>22</td><td>TCP</td><td>Zawsze (SSH)</td></tr>
  <tr><td>110</td><td>80</td><td>TCP</td><td>Zawsze (HTTP / ACME challenge)</td></tr>
  <tr><td>120</td><td>443</td><td>TCP</td><td>Zawsze (HTTPS)</td></tr>
  <tr><td>125</td><td>8443</td><td>TCP</td><td>Tylko <code>single_domain_mode = true</code></td></tr>
  <tr><td>130</td><td>51820</td><td>UDP</td><td>Zawsze (WireGuard)</td></tr>
  <tr><td>140+</td><td>np. 9090</td><td>TCP</td><td>Dynamicznie z listy <code>public_ports</code></td></tr>
</table>

<h2 class="page-break">5. Skrypty pomocnicze (<code>scripts/</code>)</h2>

<table>
  <tr><th>Skrypt</th><th>Funkcja</th></tr>
  <tr>
    <td><code>find-bootstrap-env.sh</code></td>
    <td>
      Szuka pierwszego pliku <code>/opt/*/.bootstrap.env</code> na VM.
      Używany, gdy nazwa katalogu repo może się różnić.
    </td>
  </tr>
  <tr>
    <td><code>collect-public-ports.sh</code></td>
    <td>
      Skanuje <code>services/*.yml</code> na VM. Dla wpisów z
      <code>has_domain: false</code> zbiera unikalne <code>public_port</code>.
      Zwraca JSON, np. <code>[9090,8080]</code>. Uruchamiany przez SSH lub lokalnie.
    </td>
  </tr>
  <tr>
    <td><code>terraform-sync-nsg.sh</code></td>
    <td>
      <strong>Kluczowy skrypt synchronizacji.</strong> Łączy się SSH z VM,
      zbiera porty (<code>collect-public-ports.sh</code>), czyta
      <code>DEPLOYMENT_MODE</code> z <code>.bootstrap.env</code>,
      uruchamia <code>terraform apply</code> z aktualnymi
      <code>public_ports</code> i <code>single_domain_mode</code>.
      Wywoływany przy add/update/delete usługi i zmianie domen.
    </td>
  </tr>
</table>

<h2>6. GitHub Actions — workflowy CI/CD</h2>

<p>Wszystkie workflowy (poza destroy) używają:</p>
<ul>
  <li>logowania Azure przez OIDC (<code>ARM_USE_OIDC</code>, <code>azure/login@v2</code>)</li>
  <li>odczytu IP VM z <code>terraform output -raw public_ip</code></li>
  <li>połączenia SSH jako <code>azureuser</code> z sekretu <code>SSH_PRIVATE_KEY</code></li>
</ul>

<h3>6.1 bootstrap-vm.yml — Bootstrap VM</h3>
<p><strong>Wyzwalacz:</strong> ręczny (<code>workflow_dispatch</code>)</p>
<p><strong>Wejścia:</strong> <code>resource_group_name</code>, <code>vm_name</code>, <code>wg_domain</code> (opcjonalnie), <code>kuma_domain</code> (opcjonalnie), <code>docker_subnet</code></p>
<p><strong>Kroki:</strong> Terraform apply → walidacja sekretów i podsieci → DNS wait loop → SSH → instalacja git/ansible → klon repo → <code>.bootstrap.env</code> → htpasswd → inventory Ansible → <code>bootstrap.yml</code> → znacznik <code>.bootstrap-completed</code></p>
<p><strong>Tryb:</strong> brak <code>kuma_domain</code> → <code>single</code> + <code>single_domain_mode=true</code>; z <code>kuma_domain</code> → <code>dual</code></p>

<h3>6.2 deploy.yml — Deploy</h3>
<p><strong>Wyzwalacz:</strong> push na <code>main</code> (ignoruje zmiany tylko w <code>terraform/backend.tf</code>)</p>
<p><strong>Kroki:</strong> checkout → Azure login → terraform init → SSH → <code>git pull</code> → <code>ansible/deploy.yml</code></p>

<h3>6.3 destroy.yml — Destroy Environment</h3>
<p><strong>Wyzwalacz:</strong> ręczny. <code>terraform destroy</code> — usuwa całą infrastrukturę.</p>

<h3>6.4 add-service.yml — Add Service</h3>
<p><strong>Wejścia:</strong> nazwa, vpn_ip, path, local_port, has_domain, domain, public_port, basic_auth</p>
<p><strong>Kroki:</strong> walidacja (nazwa, IP w 10.8.0.0/24, DNS, unikalność portu/domeny/backendu) → zapis <code>services/{name}.yml</code> → <code>terraform-sync-nsg.sh</code> → <code>ansible/add-service.yml</code></p>

<h3>6.5 update-service.yml — Update Service</h3>
<p>Podobnie do add, ale nadpisuje istniejący plik. Wykrywa zmianę domeny i usuwa stary certyfikat certbot. Na końcu: sync NSG + <code>ansible/update-service.yml</code>.</p>

<h3>6.6 delete-service.yml — Delete Service</h3>
<p>Usuwa certyfikat (jeśli domena), kasuje plik YAML, sync NSG, <code>ansible/update-service.yml</code> (przebudowa nginx/compose bez usługi).</p>

<h3>6.7 list-services.yml — List Services</h3>
<p>SSH na VM, Python wczytuje wszystkie <code>services/*.yml</code> i wypisuje tabelę usług.</p>

<h3>6.8 update_domains.yml — Update Domains</h3>
<p>Zmiana domen WG/Kuma. Puste <code>wg_domain</code> → FQDN Azure. Sync NSG (tryb single/dual), usuwanie starych certów, aktualizacja <code>.bootstrap.env</code>, <code>ansible/update-domains.yml</code>.</p>

<h3>6.9 update-proxy-credentials.yml — Update Auth Password</h3>
<p>Regeneruje <code>nginx/.htpasswd</code> z sekretów <code>NGINX_BASIC_AUTH_USER</code> / <code>NGINX_BASIC_AUTH_PASSWORD</code>.</p>

<h2 class="page-break">7. Ansible — playbooki i role</h2>

<h3>7.1 Playbooki</h3>
<table>
  <tr><th>Playbook</th><th>Role (kolejność)</th><th>Kiedy używany</th></tr>
  <tr>
    <td><code>bootstrap.yml</code></td>
    <td>load_config → common → docker → directories → load_services → domain_validation → deploy → certbot → containers → routing → security</td>
    <td>Pierwsze uruchomienie VM</td>
  </tr>
  <tr>
    <td><code>deploy.yml</code></td>
    <td>load_config → docker_access → directories → load_services → deploy → certbot → containers → routing</td>
    <td>Push na main</td>
  </tr>
  <tr>
    <td><code>add-service.yml</code></td>
    <td>load_config → docker_access → load_services → domain_validation → deploy → certbot → containers</td>
    <td>Nowa usługa</td>
  </tr>
  <tr>
    <td><code>update-service.yml</code></td>
    <td>jak add-service</td>
    <td>Edycja / usunięcie usługi</td>
  </tr>
  <tr>
    <td><code>update-domains.yml</code></td>
    <td>jak add-service</td>
    <td>Zmiana domen systemowych</td>
  </tr>
  <tr>
    <td><code>maintenance.yml</code></td>
    <td>common_update</td>
    <td>Konserwacja apt (brak workflow — ręcznie)</td>
  </tr>
</table>

<h3>7.2 Format pliku usługi (<code>services/*.yml</code>)</h3>
<pre>name: moja-aplikacja
vpn_ip: 10.8.0.2
path: /
local_port: 8080
has_domain: false
domain: ""
public_port: 9090
basic_auth: true</pre>

<h3>7.3 Role Ansible — szczegóły</h3>

<h4>load_config</h4>
<p>Czyta <code>/opt/{REPO}/.bootstrap.env</code>, parsuje do słownika <code>bootstrap_config</code>. Wszystkie inne role z tego korzystają.</p>

<h4>common (tylko bootstrap)</h4>
<p><code>apt update/upgrade</code>, instalacja git, curl, python3, pip, apache2-utils.</p>

<h4>common_update (maintenance)</h4>
<p>Aktualizacja pakietów, autoremove, autoclean.</p>

<h4>docker (tylko bootstrap)</h4>
<p>Repozytorium Docker CE, instalacja docker-ce i compose plugin, włączenie usługi docker.</p>

<h4>docker_access</h4>
<p>Dodaje użytkownika <code>azureuser</code> do grupy <code>docker</code>.</p>

<h4>directories</h4>
<p>Tworzy katalogi: <code>data/wireguard</code>, <code>data/kuma</code>, <code>certbot/conf</code>, <code>certbot/www</code>, <code>nginx</code>, <code>services</code>. Ustawia właściciela <code>services/</code> na azureuser.</p>

<h4>load_services</h4>
<p>Wczytuje wszystkie <code>services/*.yml</code> do faktów: <code>vpn_services</code>, <code>service_domains</code>, <code>domain_services</code>.</p>

<h4>domain_validation</h4>
<p>Sprawdza przez <code>dig</code>, czy domeny WG (i Kuma w trybie dual) oraz domeny usług wskazują na publiczny IP serwera.</p>

<h4>deploy</h4>
<p>Renderuje szablon <code>docker-compose-template.yml.j2</code> → <code>docker-compose.yml</code>. Definiuje kontenery wg-easy, uptime-kuma, nginx (porty 80/443/8443/dynamiczne public_port), certbot oraz sieć bridge <code>DOCKER_SUBNET</code>.</p>

<h4>certbot</h4>
<p>Trzy pliki zadań:</p>
<ul>
  <li><strong>system-certificates.yml</strong> — certyfikaty dla WG i Kuma</li>
  <li><strong>service-certificates.yml</strong> — certyfikaty per usługa z domeną</li>
  <li><strong>renewal.yml</strong> — cron codziennie o 03:00 na <code>certbot renew</code></li>
</ul>
<p>Szablony nginx:</p>
<ul>
  <li><code>nginx-bootstrap.conf.j2</code> — tymczasowy config pod ACME (odpowiedź „bootstrap”)</li>
  <li><code>nginx-single-domain.conf.j2</code> — WG na 443, Kuma na 8443, proxy usług</li>
  <li><code>nginx-dual-domain.conf.j2</code> — osobne domeny WG i Kuma; obsługa <code>public_port</code> bez domeny</li>
</ul>

<h4>containers</h4>
<p><code>docker compose up -d</code> w katalogu repo na VM.</p>

<h4>routing</h4>
<p>Instaluje usługę systemd <code>wg-route.service</code> — trasa <code>10.8.0.0/24</code> przez IP kontenera WG-Easy. Czeka do 120 s na dostępność gateway. Uruchamiana <strong>po</strong> starcie kontenerów.</p>

<h4>security (tylko bootstrap)</h4>
<p>Zapisuje <code>.env</code> z <code>INIT_ENABLED=false</code> — wyłącza ponowną inicjalizację WG-Easy po pierwszym bootstrapie.</p>

<h2 class="page-break">8. Pliki tworzone na maszynie wirtualnej</h2>

<p>Te pliki nie są w repozytorium Git — powstają przy bootstrapie i operacjach:</p>
<table>
  <tr><th>Ścieżka na VM</th><th>Źródło</th><th>Rola</th></tr>
  <tr><td><code>/opt/{REPO}/.bootstrap.env</code></td><td>bootstrap-vm.yml</td><td>Stała konfiguracja: domeny, tryb, podsieci, IP kontenerów</td></tr>
  <tr><td><code>/opt/{REPO}/.env</code></td><td>.env.template + envsubst</td><td>Runtime WG-Easy</td></tr>
  <tr><td><code>/opt/{REPO}/docker-compose.yml</code></td><td>Ansible deploy</td><td>Definicja kontenerów</td></tr>
  <tr><td><code>/opt/{REPO}/nginx/nginx.conf</code></td><td>Ansible certbot</td><td>Konfiguracja reverse proxy</td></tr>
  <tr><td><code>/opt/{REPO}/nginx/.htpasswd</code></td><td>bootstrap / update-proxy-credentials</td><td>Basic auth nginx</td></tr>
  <tr><td><code>/opt/{REPO}/services/*.yml</code></td><td>workflowy add/update/delete</td><td>Definicje usług użytkownika</td></tr>
  <tr><td><code>/opt/{REPO}/ansible/inventory.ini</code></td><td>bootstrap-vm.yml</td><td>Inventory Ansible (localhost)</td></tr>
  <tr><td><code>/opt/.github-bootstrap-completed</code></td><td>bootstrap-vm.yml</td><td>Zabezpieczenie przed ponownym bootstrapem</td></tr>
</table>

<h2>9. Tryby wdrożenia (single / dual)</h2>

<table>
  <tr><th>Aspekt</th><th>Single</th><th>Dual</th></tr>
  <tr><td>Warunek</td><td>Brak <code>kuma_domain</code></td><td>Podany <code>kuma_domain</code></td></tr>
  <tr><td>Domena WG</td><td><code>wg_domain</code> lub FQDN Azure</td><td><code>wg_domain</code> lub FQDN Azure</td></tr>
  <tr><td>Domena Kuma</td><td>Ta sama co WG</td><td>Osobna domena</td></tr>
  <tr><td>Port Kuma</td><td>8443 (osobny listener nginx)</td><td>443 (osobny server block)</td></tr>
  <tr><td>NSG</td><td>Otwarty port 8443</td><td>Bez 8443</td></tr>
  <tr><td>Certyfikaty</td><td>Jeden cert na WG (+ Kuma przez ten sam)</td><td>Osobne certy WG i Kuma</td></tr>
</table>

<h2>10. Sekrety i zmienne GitHub</h2>

<h3>Variables (publiczne w repo settings)</h3>
<table>
  <tr><th>Nazwa</th><th>Źródło</th></tr>
  <tr><td>AZURE_CLIENT_ID</td><td>boostrap_terraform.py → App Registration</td></tr>
  <tr><td>AZURE_TENANT_ID</td><td>az account show</td></tr>
  <tr><td>AZURE_SUBSCRIPTION_ID</td><td>az account show</td></tr>
  <tr><td>SSH_PUBLIC_KEY</td><td>output/id_ed25519.pub</td></tr>
</table>

<h3>Secrets</h3>
<table>
  <tr><th>Nazwa</th><th>Opis</th></tr>
  <tr><td>SSH_PRIVATE_KEY</td><td>Klucz prywatny SSH (cała zawartość pliku)</td></tr>
  <tr><td>WG_ADMIN_USER / WG_ADMIN_PASSWORD</td><td>Login do panelu WG-Easy</td></tr>
  <tr><td>LETSENCRYPT_EMAIL</td><td>Email do Let's Encrypt</td></tr>
  <tr><td>NGINX_BASIC_AUTH_USER / NGINX_BASIC_AUTH_PASSWORD</td><td>Basic auth dla proxy</td></tr>
</table>

<h2>11. Mapa zależności — co z czego wynika</h2>

<table>
  <tr><th>Źródło</th><th>Cel</th><th>Mechanizm</th></tr>
  <tr><td>boostrap_terraform.py</td><td>terraform/backend.tf</td><td>Zapis pliku</td></tr>
  <tr><td>boostrap_terraform.py</td><td>GitHub OIDC</td><td>Azure AD federated credential</td></tr>
  <tr><td>bootstrap-vm.yml</td><td>VM + .bootstrap.env</td><td>Terraform + SSH</td></tr>
  <tr><td>services/*.yml</td><td>docker-compose + nginx</td><td>Ansible load_services → deploy + certbot</td></tr>
  <tr><td>services/*.yml</td><td>Reguły NSG</td><td>collect-public-ports → terraform-sync-nsg</td></tr>
  <tr><td>.bootstrap.env</td><td>Wszystkie role Ansible</td><td>load_config</td></tr>
  <tr><td>deploy.yml (workflow)</td><td>ansible/deploy.yml</td><td>git pull + SSH</td></tr>
  <tr><td>wg-route.service</td><td>Komunikacja z klientami VPN</td><td>Trasa hosta → kontener WG-Easy</td></tr>
</table>

<h3>Przepływ dodania usługi bez domeny (public_port)</h3>
<ol>
  <li>Użytkownik uruchamia <strong>Add Service</strong> z <code>has_domain=false</code>, <code>public_port=9090</code></li>
  <li>Workflow zapisuje <code>services/apka.yml</code> na VM</li>
  <li><code>terraform-sync-nsg.sh</code> dodaje port 9090 do NSG w Azure</li>
  <li>Ansible regeneruje <code>docker-compose.yml</code> (mapowanie 9090:9090) i <code>nginx.conf</code> (listen 9090 → proxy na vpn_ip:local_port)</li>
  <li><code>docker compose up -d</code> stosuje zmiany</li>
</ol>

<hr>
<p class="meta" style="margin-top: 32px;">
  Koniec sprawozdania. Plik wygenerowany automatycznie z repozytorium
  <strong>validationtest</strong>.
</p>

</body>
</html>
"""


def main() -> int:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(HTML, encoding="utf-8")
    print(f"Zapisano: {HTML_PATH}")

    for converter in (
        [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(DOCS_DIR),
            str(HTML_PATH),
        ],
        [
            "firefox",
            "--headless",
            f"--print-to-pdf={PDF_PATH}",
            f"file://{HTML_PATH}",
        ],
    ):
        try:
            result = subprocess.run(
                converter,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            continue

        if result.returncode == 0:
            # LibreOffice names output from HTML basename
            lo_pdf = DOCS_DIR / "sprawozdanie-repozytorium.pdf"
            if not lo_pdf.exists():
                lo_pdf = DOCS_DIR / "sprawozdanie-repozytorium.pdf"
            if lo_pdf.exists() or PDF_PATH.exists():
                final = PDF_PATH if PDF_PATH.exists() else lo_pdf
                print(f"Wygenerowano PDF: {final}")
                return 0

        print(f"Próba {converter[0]} nieudana: {result.stderr or result.stdout}")

    print(
        "Nie udało się wygenerować PDF automatycznie.\n"
        f"Otwórz w przeglądarce i wydrukuj do PDF: {HTML_PATH}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
