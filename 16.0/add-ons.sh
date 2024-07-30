      mkdir -p /workspace/odoo
      cd /workspace/odoo
      mkdir -p addons-available addons-enabled
      cd addons-available
      git clone --depth=1 -b 16.0 https://github.com/OCA/partner-contact
      git clone --depth=1 -b 16.0 https://github.com/OCA/web.git
      git clone --depth=1 -b 16.0 https://github.com/OpenEMS/odoo-openems.git
      cd ../addons-enabled
      ln -s ../addons-available/partner-contact/partner_firstname
      ln -s ../addons-available/web/web_m2x_options
      ln -s ../addons-available/odoo-openems/openems
      odoo -d prod --addons-path=/workspace/odoo/addons-enabled -i base,partner_firstname,web_m2x_options,stock,openems

