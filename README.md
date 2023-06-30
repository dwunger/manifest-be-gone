# manifest-be-gone
Manager to remove stray manifest files that confuse Steam's launcher

CLI wizard walks through all drives for common steam install locations,
catches stray appmanifests and manifests linked to empty directories.
These stragglers cause issues with launching & installing games if they 
weren't deleted the way Steam expects.
