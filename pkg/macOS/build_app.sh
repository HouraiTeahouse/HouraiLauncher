# Build *.app
BUILDDIR="build"
APP="Fantasy_Crescendo"
EXE="dist/launcher"
APP_DIR="$BUILDDIR/$APP.app"
mkdir -p $APP_DIR/Contents
mkdir -p $APP_DIR/Contents/MacOS
mkdir -p $APP_DIR/Contents/Frameworks
mkdir -p $APP_DIR/Contents/Resources

cp pkg/macOS/Info.plist $BUILDDIR/$APP.app/Contents

APPEXE="$APP_DIR/Contents/MacOS/$APP"
cp $EXE $APPEXE

# Build *.dmg file
git clone https://github.com/andreyvit/yoursway-create-dmg.git ./create-dmg
./create-dmg/create-dmg \
  --volname "Fantasy Crescendo Installer" \
  dist/fc_installer.dmg \
  $APP_DIR/
