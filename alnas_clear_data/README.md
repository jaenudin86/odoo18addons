# Simple Clear Data

This module is designed to help you remove all data from a model.

## Installation

To install this module:

1. Download the module and place it in Odoo **Custom Addons** folder.
2. Restart Odoo Server
2. Go to Odoo UI and Enable **Debug Mode** then open the **Apps** menu.  
3. Refresh the list by clicking **Update Apps List**.  
4. Finally, you will see 'Simple Clear Data' module and click the **Install** button.

## Configuration

Navigate to **Users** and assign the permission **Clear Data Access** to the intended user.

## How To Use
1. Go to **Settings** => **Technical** => **Clear Data** => **Clear Data Transaction**
2. Choose Model
3. Click **Clear** button

## Notes

Some Odoo models have additional constraints that prevent direct deletion if dependent records still exist.  
If you receive an error while deleting a model (for example, `stock.picking`), remove the related records first, such as:
- For `stock.picking` → delete `stock.move` and `stock.move.line`.  
Once the dependent data is cleared, you can rerun the wizard to remove the main record.