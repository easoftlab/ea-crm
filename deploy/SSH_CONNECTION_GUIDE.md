# SSH Connection Guide for EA CRM

## 📋 **Connection Details**

- **IP Address:** 145.223.77.49
- **Port:** 65002 (non-standard port)
- **Username:** u539052962
- **Password:** Emon_@17711

## 🚀 **Connection Methods**

### **Option 1: Command Line**
```bash
# Windows (PowerShell/Command Prompt)
ssh -p 65002 u539052962@145.223.77.49

# Mac/Linux Terminal
ssh -p 65002 u539052962@145.223.77.49
```

### **Option 2: PuTTY (Windows)**
1. Download PuTTY from: https://www.putty.org/
2. Open PuTTY
3. Enter connection details:
   - **Host Name:** 145.223.77.49
   - **Port:** 65002
4. Click "Open"
5. Enter username: `u539052962`
6. Enter password: `Emon_@17711`

### **Option 3: VS Code (Recommended)**
1. Install VS Code
2. Install "Remote - SSH" extension
3. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
4. Type "Remote-SSH: Connect to Host"
5. Enter: `u539052962@145.223.77.49:65002`

## 🔧 **Quick Setup Commands**

Once connected, run these commands:

```bash
# Navigate to CRM directory
cd crm

# Verify files are present
ls -la

# Run quick setup
chmod +x quick_setup.sh
./quick_setup.sh
```

**Expected Files:**
- `app/` (directory)
- `config.py`
- `requirements.txt`
- `wsgi.py`
- `quick_setup.sh`
- `.htaccess`

## 🆘 **Troubleshooting**

### **Connection Issues:**
1. **Port 65002 blocked:** Try using a VPN or contact your hosting provider
2. **Authentication failed:** Double-check username and password
3. **Connection timeout:** Check your internet connection

## 📚 **Documentation**

For complete deployment information, see:
- **[Deployment & DevOps Guide](docs/04_DEPLOYMENT_AND_DEVOPS_GUIDE.md)** - Comprehensive deployment documentation
- **[Project Overview](docs/01_PROJECT_OVERVIEW_AND_ARCHITECTURE.md)** - System architecture and setup

---

**For detailed deployment instructions, see `/docs/04_DEPLOYMENT_AND_DEVOPS_GUIDE.md`** 