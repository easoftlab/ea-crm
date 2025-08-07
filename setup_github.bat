@echo off
echo 🚀 EA CRM GitHub Setup
echo ======================
echo.

echo Step 1: Initializing Git repository...
git init

echo.
echo Step 2: Adding all files...
git add .

echo.
echo Step 3: Committing files...
git commit -m "Initial commit with EA CRM application"

echo.
echo Step 4: Setting main branch...
git branch -M main

echo.
echo Step 5: Please enter your GitHub repository URL
echo Example: https://github.com/yourusername/ea-crm.git
set /p repo_url="GitHub repository URL: "

echo.
echo Step 6: Adding remote repository...
git remote add origin %repo_url%

echo.
echo Step 7: Pushing to GitHub...
git push -u origin main

echo.
echo ✅ Setup complete!
echo.
echo Next steps:
echo 1. Go to your GitHub repository
echo 2. Click Settings → Secrets and variables → Actions
echo 3. Add FTP_SERVER, FTP_USERNAME, and FTP_PASSWORD secrets
echo 4. Test deployment by making a change and pushing
echo.
pause 