# Restore Symmetry

Restory Symmetry is a fork of Remirror, an addon that was developed by Philip Lafleur and posted on the Blender wiki and tracker. (https://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Mesh/Remirror)

Its purpose is to reestablish symmetry in a mirrored mesh after sculpting (which does not keep perfect symmetry in all cases) or other mesh editing that disrupts symmetry.

I edited the addon to add support for restoring symmetry of shape keys. 

## Installing

Download the .py file by either clicking on it and then clicking RAW, or download the whole master branch with all addons (currently only this one exists). Extract to your addon folder.


## Usage

Please read [https://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Mesh/Remirror](https://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Mesh/Remirror) to see how it works. 

It's pretty simple though, just select a mesh in object mode and do Object - Mirror - Restore Symmetry or just Restore Symmetry from the spacebar search menu. It will fail if your mesh doesn't have a loop through the middle of the mesh.

If you want to add a hotkey you can add it in 3dview - Object mode and the command is: 
```
mesh.restoresymmetry
```

## Authors

* **Philip Lafleur** - *Original creator of the Remirror addon*
* **Henrik Berglund** - *Edits to the addon*

## License

GPL

## Acknowledgements

Thanks to the original author Philip Lafleur for the original Remirror addon.
