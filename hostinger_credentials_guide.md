# 🔐 **Hostinger FTP Credentials Guide**

## **How to Find Your Hostinger FTP Credentials**

### **Step 1: Log into Hostinger**
1. Go to **hostinger.com**
2. Click **"Login"** in the top right
3. Enter your email and password

### **Step 2: Access Your Hosting Control Panel**
1. After logging in, you'll see your hosting packages
2. Click **"Manage"** next to your hosting package
3. This opens your **hPanel** (Hostinger Control Panel)

### **Step 3: Find FTP Credentials**
1. In the left sidebar, look for **"Files"** section
2. Click on **"FTP Accounts"**
3. You'll see your FTP credentials listed

### **Step 4: Your FTP Information**
You'll need these details for GitHub secrets:

#### **FTP_SERVER**
- Usually your domain name (e.g., `yourdomain.com`)
- Or sometimes `ftp.yourdomain.com`
- Check what's listed in your FTP accounts

#### **FTP_USERNAME**
- Your FTP username (usually starts with `u` followed by numbers)
- Example: `u539052962`

#### **FTP_PASSWORD**
- Your FTP password
- The password you set for your FTP account

### **Step 5: Test Your FTP Credentials**
You can test these credentials using any FTP client like FileZilla:
1. Download **FileZilla** (free FTP client)
2. Enter your FTP details:
   - **Host**: Your FTP server
   - **Username**: Your FTP username
   - **Password**: Your FTP password
   - **Port**: 21 (usually)
3. Click **"Quickconnect"**
4. If it connects successfully, your credentials are correct

### **Step 6: Add to GitHub Secrets**
Once you have your credentials:
1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Add these secrets:
   - `FTP_SERVER`: Your FTP server
   - `FTP_USERNAME`: Your FTP username
   - `FTP_PASSWORD`: Your FTP password

---

**Need Help?**
- Contact Hostinger support if you can't find your FTP credentials
- They can help you reset or find your FTP information 