# Hourai Launcher

[![Windows Build
status](https://ci.appveyor.com/api/projects/status/jxlwb36kfc8s05ff?svg=true)](https://ci.appveyor.com/project/james7132/hourailauncher)
[![Travis Build
Status](https://travis-ci.org/HouraiTeahouse/HouraiLauncher.svg?branch=master)](https://travis-ci.org/HouraiTeahouse/HouraiLauncher)
[![Discord](https://discordapp.com/api/guilds/151219753434742784/widget.png)](https://discord.gg/VuZhs9V)

A cross platform game launcher/patcher.

## Usage

HouraiLauncher is meant to be built as a standalone executable via PyInstaller.
It presents a cross-platform GUI via PyQt5. To use this with a game project,
you'll need to configure it, and build your own copy.

**NOTE:** For the patching functionality to work, the install directory for both
the patcher and the game (it must be the same directory) must be writable
without evevated permissions. The game will launch properly, but will not patch
over time. This includes Window's "Program Files" folder. For such situations,
we suggest installing under "C:\Games" or something similar.

## Configuration

Configuration of the launcher is done via the config.json file. Below is
documentation

```javascript
{
  // The name of the project. This will be used to title the launcher window.
  "project": "Fantasy Crescendo",

  // The remote HTTP endpoint to fetch updates from.
  // Certain patterns will be replaced at runtime.
  // {project} => A URL safe version of the project name. Fantasy Crescendo
  //              becomes "fantasy-crescendo"
  // {branch}  => The target branch for deployment. See the branches information
  //              below
  "index_endpoint": "https://patch.houraiteahouse.net/{project}/{branch}",

  // The logo image for the game
  "logo": "img/logo.png",

  // The platform dependent name of the game binary to launch after checking for
  // updates
  "game_binary": {
    "Windows": "fc.exe",
    "Linux": "fc.x86_64"
  },

  // Optional custom command line arguments to pass to the executable to launch
  // the game
  "launch_flags":{
    "Linux": ['-screenheight', '100']
  },

  // The respective deployment branches available. Maps from one historical
  // source control branch to a user-facing string.
  "branches" : {
    "master": "Stable",
    "develop": "Development"
  }
}
```

## Update Payloads

This patcher expects a JSON payload from the specified `index_endpoint` in the
following format: ```javascript { // The last time the game was updated
"last_updated": 1495329322

// The base download URL for the game files. "base_url":
"https://patch.houraiteahouse.net"

// The format for building the // {base} => base_url as described above //
{project} => URL-safe encoded project name // {branch} => The source control
branch associated with the build. // {filepath} => The path of the file relative
to the root folder // {filehash} => The SHA-256 hash of the file "url_format":
"{base}/{project}/{branch}/{filename}_{filehash}",

// A set of all files me "files": { // Keys are the relative path to the root
folder. // This file list is flat. "fc.exe": { // The file's SHA-256 hash
"sha256": "341c76ab4124d205ea796850984d042aefae420226f5017983fab00e435d746e",

      // The size of the file in bytes.
      "size": 77723722
    }

},

"directories": { "fc_Data": { // The action to perform when updating // Can be a
list of actions // Availble Actions: // clean => Deletes all files not describe
by a prior step. "action": "clean" } } } ```
