from maya.cmds import*
shelfButton(
	parent="Custom",  
	enable=1, 
	manage=1, 
	visible=1, 
	annotation="Launch Dliang SP Tool Maya UI", 
	image1="pythonFamily.png", 
	imageOverlayLabel="SP", 
	sourceType="python", 
	command="import DliangSP_Maya.ui;reload(DliangSP_Maya.ui)" 
	)