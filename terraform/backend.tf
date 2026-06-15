terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "tfstate82310ae3"
    container_name       = "tfstate"
    key                  = "secure-vpn-platform.tfstate"
  }
}
