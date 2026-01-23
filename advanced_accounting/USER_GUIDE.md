# User Guide - Advanced Accounting Module

## Table of Contents

1. [Budget Management](#budget-management)
2. [Asset Management](#asset-management)
3. [Cost Center Management](#cost-center-management)
4. [Payment Follow-up](#payment-follow-up)
5. [Reports](#reports)

---

## Budget Management

### Creating a Budget

1. Navigate to: **Advanced Accounting > Budgets > Budgets**
2. Click **Create**
3. Fill in the form:
   - Budget Name: e.g., "2026 Annual Budget"
   - Budget Code: e.g., "BUD-2026"
   - Start Date: 2026-01-01
   - End Date: 2026-12-31
4. Add Budget Lines:
   - Click "Add a line"
   - Select Analytic Account
   - Select General Account (optional)
   - Enter Planned Amount
5. Click **Save**

### Budget Approval Workflow

1. **Draft**: Initial creation state
2. Click **Confirm** to submit for review
3. **Confirmed**: Waiting for approval
4. Manager clicks **Approve**
5. **Approved**: Budget is active
6. Click **Done** when period ends

### Monitoring Budget

- **Planned Amount**: Budgeted amount
- **Practical Amount**: Actual spent (auto-calculated)
- **Theoretical Amount**: Expected spent at current date
- **Achievement %**: (Practical / Planned) × 100

### Budget Alerts

System will show warnings when:
- Actual spending exceeds budget
- Spending rate is higher than expected

---

## Asset Management

### Creating an Asset

1. Navigate to: **Advanced Accounting > Assets > Assets**
2. Click **Create**
3. Fill in Asset Information:
   - Asset Name: e.g., "Office Building"
   - Asset Code: e.g., "ASSET-001"
   - Asset Type: Purchase or Sale
   - Date: Purchase date

4. Enter Asset Values:
   - Original Value: Purchase price
   - Salvage Value: Residual value at end of life

5. Configure Depreciation:
   - Method: Linear or Degressive
   - Number of Depreciations: 5 years = 5 entries
   - Period Length: Monthly, Quarterly, or Yearly
   - Prorata Temporis: Check if first depreciation is partial

6. Set Accounting Accounts:
   - Asset Account: Fixed Asset account
   - Depreciation Account: Accumulated Depreciation
   - Expense Account: Depreciation Expense
   - Journal: Asset/Depreciation Journal

7. Click **Save**
8. Click **Validate** to activate

### Depreciation Methods

**Linear Method**:
- Equal depreciation each period
- Formula: (Original Value - Salvage) / Number of Periods

**Degressive Method**:
- Higher depreciation in early years
- Uses degressive factor (e.g., 0.3 = 30%)

### Processing Depreciation

1. System auto-generates depreciation lines
2. View in "Depreciation Board" tab
3. Click **Post Entry** on each line to create journal entry
4. Or batch process using automation

### Asset Disposal

1. Open asset
2. Click **Close Asset**
3. Create manual journal entry for disposal

---

## Cost Center Management

### Creating Cost Centers

1. Navigate to: **Advanced Accounting > Cost Centers > Cost Centers**
2. Click **Create**
3. Fill in:
   - Code: e.g., "CC-001"
   - Name: e.g., "Sales Department"
   - Parent Cost Center: For hierarchical structure
   - Manager: Responsible person

### Using Cost Centers

1. **Link to Analytic Accounts**:
   - Open Analytic Account
   - Set Cost Center field

2. **Link to Journal Entries**:
   - When creating entries
   - Set Cost Center field

3. **View Analysis**:
   - Total Revenue: Income allocated to cost center
   - Total Cost: Expenses allocated to cost center
   - Balance: Revenue - Cost

### Cost Center Hierarchy

Create parent-child relationships:
```
Company
├── Sales Department
│   ├── North Region
│   └── South Region
└── Operations
    ├── Manufacturing
    └── Logistics
```

---

## Payment Follow-up

### Follow-up Configuration

1. Navigate to: **Advanced Accounting > Payment Follow-up > Follow-up Levels**
2. Default levels are pre-configured:
   - Level 1: 15 days after due date
   - Level 2: 30 days after due date
   - Level 3: 45 days after due date

3. Customize each level:
   - Edit delay period
   - Customize email message
   - Enable/disable email sending
   - Set manual action requirements

### Running Follow-up

1. Navigate to: **Advanced Accounting > Payment Follow-up > Follow-up History**
2. System automatically creates follow-up lines for overdue invoices
3. Review follow-up lines
4. Click **Send Email** to send reminders

### Manual Follow-up

1. Open Partner form
2. Go to "Payment Follow-up" tab
3. View:
   - Last Follow-up Date
   - Current Follow-up Level
   - Follow-up History

### Follow-up Actions

For each follow-up line, you can:
- Send email automatically
- Record phone call
- Schedule visit
- Take manual action (e.g., legal action)

---

## Reports

### Budget Reports

1. Navigate to: **Advanced Accounting > Budgets**
2. Select budget
3. View Summary tab for:
   - Total Planned vs Actual
   - Achievement percentage
   - Variance analysis

### Asset Reports

1. Navigate to: **Advanced Accounting > Assets**
2. Filter assets by:
   - Status (Draft, Running, Closed)
   - Asset Type
   - Date

3. View:
   - Book Value
   - Accumulated Depreciation
   - Remaining Value

### Cost Center Reports

1. Navigate to: **Advanced Accounting > Cost Centers**
2. Select cost center
3. View:
   - Revenue vs Cost
   - Budget vs Actual
   - Trend analysis

### Custom Reports

Use Report Wizard:
1. Click **Print Report** button
2. Select:
   - Report Type
   - Date Range
   - Filters
3. Click **Print** to generate PDF/Excel

---

## Best Practices

### Budget Management
- Review budgets monthly
- Adjust forecasts quarterly
- Link all expenses to budgets
- Set up alerts for overruns

### Asset Management
- Regular asset inventory checks
- Keep supporting documents
- Review depreciation schedules annually
- Process depreciation monthly

### Cost Centers
- Align with org structure
- Review allocations quarterly
- Train users on proper coding
- Monitor performance metrics

### Payment Follow-up
- Run follow-up weekly
- Customize messages for different customers
- Track follow-up results
- Escalate when necessary

---

## Tips & Tricks

1. **Keyboard Shortcuts**:
   - Ctrl+K: Search menu
   - Ctrl+/: Focus search
   - Alt+Shift+N: New record

2. **Bulk Operations**:
   - Use list view actions
   - Export to Excel for analysis
   - Import from templates

3. **Filters & Groups**:
   - Save custom filters
   - Use group by for analysis
   - Create dashboard views

4. **Automation**:
   - Set up scheduled actions
   - Use email templates
   - Configure automated alerts

---

## FAQ

**Q: Can I modify an approved budget?**
A: Yes, but best practice is to create a new version.

**Q: How do I handle asset improvements?**
A: Create new asset entry or adjust original value.

**Q: Can I have multi-currency assets?**
A: Yes, system uses company currency for calculations.

**Q: How to delete a cost center?**
A: Archive it instead to preserve history.

---

## Support

For additional help:
- Check Odoo official documentation
- Contact your system administrator
- Reach out to module developer
