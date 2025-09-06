#!/bin/bash
# =========================================
# antiX Modern Desktop + WhiteSur + All-Apps Menu
# Replaces default desktop with:
# Thunar + Plank + XFCE Panel + Whisker Menu
# Applies WhiteSur GTK + Icon theme
# =========================================

# Update system
sudo apt update
sudo apt upgrade -y

# -------------------------
# Install essential apps
# -------------------------
sudo apt install -y git thunar thunar-volman plank xfce4-panel xfce4-whiskermenu-plugin \
    lxappearance arc-theme papirus-icon-theme faenza-icon-theme \
    gtk2-engines-murrine gtk2-engines-pixbuf nitrogen exfat-fuse exfat-utils ntfs-3g

# -------------------------
# Set Thunar as default file manager
# -------------------------
xdg-mime default Thunar.desktop inode/directory application/x-gnome-saved-search

# -------------------------
# Disable Rox-Filer if present
# -------------------------
if [ -f ~/.fluxbox/startup ]; then
    sed -i '/rox-filer/d' ~/.fluxbox/startup
fi
if [ -f ~/.icewm/startup ]; then
    sed -i '/rox-filer/d' ~/.icewm/startup
fi

# -------------------------
# Configure auto-start for Plank and XFCE Panel (with Whisker Menu)
# -------------------------
XINITRC="$HOME/.xinitrc"
# Backup existing .xinitrc
if [ -f $XINITRC ]; then
    cp $XINITRC "${XINITRC}.bak"
fi
# Add startup commands if not already present
grep -qxF "plank &" $XINITRC || echo "plank &" >> $XINITRC
grep -qxF "xfce4-panel &" $XINITRC || echo "xfce4-panel &" >> $XINITRC

# -------------------------
# Install WhiteSur GTK Theme
# -------------------------
cd $HOME
git clone https://github.com/vinceliuice/WhiteSur-gtk-theme.git --depth=1
cd WhiteSur-gtk-theme
chmod +x install.sh
./install.sh -c light   # light theme, use '-c dark' for dark
cd ..
rm -rf WhiteSur-gtk-theme

# -------------------------
# Install WhiteSur Icon Theme
# -------------------------
git clone https://github.com/vinceliuice/WhiteSur-icon-theme.git --depth=1
cd WhiteSur-icon-theme
chmod +x install.sh
./install.sh
cd ..
rm -rf WhiteSur-icon-theme

# -------------------------
# Apply GTK and icon themes via lxappearance
# -------------------------
echo "Run 'lxappearance' to select 'WhiteSur' GTK theme and 'WhiteSur' icons."

# -------------------------
# Set wallpaper directory (optional)
# -------------------------
mkdir -p ~/Pictures/Wallpapers
echo "Place your wallpapers in ~/Pictures/Wallpapers and run 'nitrogen' to set them."

# -------------------------
# Finished
# -------------------------
echo "=============================="
echo "Setup complete!"
echo "Log out and log back in to see your new macOS-style desktop."
echo "Thunar is now the default file manager."
echo "Plank dock and XFCE panel with Whisker Menu are fully integrated."
echo "Use 'lxappearance' to apply WhiteSur themes and icons."
echo "Enjoy your modern antiX setup!"
