# manifest-be-gone
Manager to remove stray manifest files that confuse Steam's launcher

CLI wizard walks (muncher.py) through all drives for common steam install 
locations, catches stray appmanifests and manifests linked to empty 
directories (1KB). These stragglers cause issues with launching & 
installing games if they weren't deleted the way Steam expects.

**Will not delete anything without first getting user confirmation.**
Elevation to admin used by default, but is only needed for handling
'read-only' directories, which should not be causing issues anyway.
This can safely be dismissed and will still clean up manifests.

manifestGUI.py inherits from Muncher but accomplishes most of the
same functionality without need for the CLI. Both modules work 
independent of one another.

_TODO:
*Selecting drive appropriately does not update manifest list. - manifestGUI
*Does not catch manifests linked to empty folders - manifestGUI_
