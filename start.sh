#!/bin/bash

mkdir -p ~/.config/fcitx
cat > ~/.config/fcitx/profile <<EOF
[Profile]
IMList=Pinyin:True,Keyboard:False
DefaultIM=Pinyin
EOF

echo "Starting supervisord..."
exec /usr/bin/supervisord -c /app/supervisord.conf
