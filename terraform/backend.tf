terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "tfstate5bbd618b"
    container_name       = "tfstate"
    key                  = "secure-vpn-platform.tfstate"
  }
}
