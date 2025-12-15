# GitHub Repository Setup Instructions

## Step 1: Create Private Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `sl_daily_not_contacted_leads` (or your preferred name)
3. Description: "SmartLead Daily Not Contacted Leads Tracker - Automated daily tracking system"
4. **Set to Private** (important!)
5. **Do NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 2: Push to GitHub

After creating the repository, GitHub will show you commands. Use these:

```bash
cd /home/ubuntu/sl_daily_not_contacted_leads

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/sl_daily_not_contacted_leads.git

# Push to GitHub
git push -u origin main
```

### If you need to authenticate:

**Option 1: Personal Access Token (Recommended)**
1. Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
2. Generate new token with `repo` scope
3. Use token as password when pushing:
```bash
git push -u origin main
# Username: YOUR_USERNAME
# Password: YOUR_PERSONAL_ACCESS_TOKEN
```

**Option 2: SSH (If you have SSH keys set up)**
```bash
# Add SSH remote instead
git remote set-url origin git@github.com:YOUR_USERNAME/sl_daily_not_contacted_leads.git
git push -u origin main
```

## Step 3: Verify

Check your GitHub repository - you should see all files:
- `smartlead_campaign_lead_tracker.py`
- `run_tracker.sh`
- `setup_cron.sh`
- `README.md`
- `.gitignore`
- All documentation files

## Important Notes

✅ **Credentials are NOT included** - `google_credentials.json` is in `.gitignore`
✅ **Logs are NOT included** - All `.log` files are excluded
✅ **Repository is private** - Only you can access it

## Future Updates

To push future changes:

```bash
cd /home/ubuntu/sl_daily_not_contacted_leads
git add .
git commit -m "Description of changes"
git push
```
