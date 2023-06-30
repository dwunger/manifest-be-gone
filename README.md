# manifest-be-gone
Manager to remove stray manifest files that confuse Steam's launcher

CLI wizard walks through all drives for common steam install locations,
catches stray appmanifests and manifests linked to empty directories (1KB).
These stragglers cause issues with launching & installing games if they 
weren't deleted the way Steam expects.

**Will not delete anything without first getting user confirmation.**
Elevation to admin used by default, but is only needed for handling
'read-only' directories, which should not be causing issues anyway.
This can safely be dismissed and will still clean up manifests.


