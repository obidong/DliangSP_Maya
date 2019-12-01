from maya.cmds import*
import os


def refresh_state(*args):
    global init_state
    global port_num
    port_num = textFieldGrp("port_textGrp", q=1, tx=1)
    opened_ports = commandPort(q=1, lp=1)
    if (":" + port_num) in opened_ports:
        init_state = 1
        iconTextButton("toggle_btn", e=1, i=icon_path + 'sync_on.png')
    else:
        init_state = 0
        iconTextButton("toggle_btn", e=1, i=icon_path + 'sync_off.png')


def toggle_port(*args):
    global init_state
    global port_num
    if init_state == 0:
        try:
            commandPort(n=":" + port_num, sourceType="python")
            iconTextButton("toggle_btn", e=1, i=icon_path + 'sync_on.png')
            init_state = 1
        except:
            init_state = 0
            iconTextButton("toggle_btn", e=1, i=icon_path + 'sync_disabled.png')
    else:
        iconTextButton("toggle_btn", e=1, i=icon_path + 'sync_off.png')
        commandPort(n=":" + port_num, cl=1)
        init_state = 0

current_dir = os.path.dirname(__file__)
icon_path = os.path.join(current_dir, 'icons/')
port_num = "9001"
init_state = 0


if window("DliangSP_Maya_UI", exists=1):
    deleteUI("DliangSP_Maya_UI")

window("DliangSP_Maya_UI", t="DliangSP_Maya_UI", w=200, h=60, s=0, rtf=1)
columnLayout()
rowLayout(nc=3)
text('Port')
textFieldGrp("port_textGrp", tx=port_num, changeCommand=refresh_state)
iconTextButton("toggle_btn", style='iconOnly', image=(icon_path + 'sync_off.png'), c=toggle_port)
setParent("..")
setParent("..")
showWindow("DliangSP_Maya_UI")
refresh_state()
