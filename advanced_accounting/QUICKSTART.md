# Quick Start Guide - Advanced Accounting

Get started with Advanced Accounting module in 5 minutes!

## Prerequisites

- Odoo 18.0 installed
- Admin access to Odoo
- Basic accounting knowledge

## Installation (2 minutes)

1. **Upload Module**
   ```bash
   # Extract ZIP file
   unzip advanced_accounting.zip -d /path/to/odoo/addons/
   
   # Or use Odoo UI
   # Apps > Upload Module > Select ZIP file
   ```

2. **Update Apps List**
   - Go to Apps
   - Click "Update Apps List"
   - Wait for completion

3. **Install Module**
   - Search "Advanced Accounting"
   - Click "Install"

## First Budget (1 minute)

1. Go to: **Advanced Accounting > Budgets > Budgets**
2. Click **Create**
3. Fill in:
   - Name: "My First Budget"
   - Start Date: Today
   - End Date: End of year
4. Click "Add a line" in Budget Lines
5. Select an Analytic Account
6. Enter Planned Amount: 10000
7. **Save** and **Confirm**

✅ Your first budget is created!

## First Asset (1 minute)

1. Go to: **Advanced Accounting > Assets > Assets**
2. Click **Create**
3. Fill in:
   - Name: "Office Computer"
   - Original Value: 5000
   - Method: Linear
   - Number of Depreciations: 5
   - Period: Yearly
4. Set accounts (use any Fixed Asset accounts)
5. **Save** and **Validate**

✅ System will generate depreciation schedule automatically!

## First Cost Center (30 seconds)

1. Go to: **Advanced Accounting > Cost Centers**
2. Click **Create**
3. Fill in:
   - Code: "CC-SALES"
   - Name: "Sales Department"
4. **Save**

✅ Cost center ready to use!

## Configure Follow-up (30 seconds)

Default levels are already configured! Just customize:

1. Go to: **Advanced Accounting > Payment Follow-up > Follow-up Levels**
2. Click on "Level 1: First Reminder"
3. Adjust delay if needed (default: 15 days)
4. Customize email message
5. **Save**

✅ Payment follow-up is active!

## Next Steps

### Learn More
- Read [USER_GUIDE.md](USER_GUIDE.md) for detailed instructions
- Check [README.md](README.md) for feature overview
- Review [INSTALL.md](INSTALL.md) for advanced setup

### Configure
1. **Chart of Accounts**: Setup asset and depreciation accounts
2. **Journals**: Create journals for assets and depreciation
3. **Permissions**: Assign user groups
4. **Email Templates**: Customize follow-up emails

### Use
1. **Create Budgets**: Plan your finances
2. **Track Assets**: Manage fixed assets
3. **Monitor Costs**: Track by department
4. **Follow-up**: Collect overdue payments

## Common Tasks

### Track Spending Against Budget
```
1. Create budget with planned amounts
2. Post journal entries with analytic accounts
3. View budget to see practical amounts
4. Check achievement percentage
```

### Depreciate Assets
```
1. Create asset with depreciation settings
2. Validate to generate schedule
3. Click "Post Entry" on depreciation lines
4. Or use scheduled action for automation
```

### Analyze by Cost Center
```
1. Create cost centers
2. Link analytic accounts to cost centers
3. Post entries with analytic accounts
4. View cost center to see totals
```

### Send Payment Reminders
```
1. System auto-creates follow-up lines for overdue invoices
2. Review in Follow-up History
3. Click "Send Email" to send reminder
4. Track results
```

## Tips for Success

1. **Start Small**: Create one budget, one asset, one cost center
2. **Test First**: Use test data before going live
3. **Train Users**: Share USER_GUIDE.md with your team
4. **Regular Review**: Check budgets and depreciation monthly
5. **Customize**: Adjust settings to match your needs

## Need Help?

- Check log files: `/var/log/odoo/odoo-server.log`
- Enable debug mode: Settings > Activate Developer Mode
- Review documentation files
- Contact support

## Congratulations! 🎉

You're ready to use Advanced Accounting module!

Start creating budgets, tracking assets, and managing your finances more effectively.
