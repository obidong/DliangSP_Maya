# coding: utf-8
from maya.cmds import*
import pymel.core as pm
import json, os, re

render_plugin_dict = {"Arnold": "aiStandardSurface", "Vray": "VRayMtl", "Renderman_PxrDisney": "PxrDisney", "RedShift": "RedshiftMaterial"}


def run(material_name, channel_dict, render_plugin):
    """
    material_name: name of the material
    channel_dict: {
    "baseColor":["outColor","D:/path/to/exported/sword_baseColor.1001.tiff", "sRGB","sword_baseColor.1001.tiff"],
    "specularRoughness":["outAlpha","D:/path/to/exported/sword_Roughness.1001.tiff", "Raw","sword_Roughness.1001.tiff"]
    }
    render_plugin: "Arnold"
    """

    if channel_dict is None:
        print ("No channel information found")
        return None
    if material_name == "":
        material_name = "temp_mat"

    target_obj_list = ls(sl=1)
    target_shader = None
    shader_exists = False

    for shd in pm.ls(materials=True):
        if [c for c in shd.classification() if 'shader/surface' in c and material_name in str(shd)]:
            shader_exists = True
            target_shader = str(shd)
        elif [c for c in shd.classification() if 'shader/surface' in c and material_name not in str(shd)]:
            pass
    if shader_exists:
        print "=== Shader Exists ===\n=== Update Mode ==="
        target_sg = listConnections(target_shader, d=1, t="shadingEngine")[0]
        update_textures(target_shader, channel_dict, render_plugin, target_sg)
    else:
        print "=== Create New Shading Network ==="
        create_network(target_obj_list, material_name, channel_dict, render_plugin)


def create_network(target_obj_list, material_name, channel_dict, render_plugin):
    print "=== Start Creating %s Network ===" % render_plugin
    # create a shader and assign to selection
    current_shader = shadingNode(render_plugin_dict[render_plugin], name=material_name, asShader=1, skipSelect=1)
    current_sg = sets(renderable=True, noSurfaceShader=True, empty=1, name=current_shader+"SG")
    connectAttr("%s.outColor" % current_shader, "%s.surfaceShader" % current_sg)

    if render_plugin == "Arnold":
        try:
            loadPlugin('mtoa')
            arnold_version = pluginInfo('mtoa', q=1, version=1)
            if int(arnold_version.split('.')[0]) < 2:
                print "Arnold version too low. Please update mtoa to 2.0 or above"
                return None
        except:
            print "Cannot find" + render_plugin + " plugin."
            return None

    if render_plugin == "Vray":
        print "==== Vray ===="
        try:
            loadPlugin('vrayformaya')
            vray_version = pluginInfo('vrayformaya', q=1, version=1)
            if int(vray_version.split('.')[0]) < 4:
                print "Vray version too low. Please update to 4.0 or above"
                return None
        except:
            print "Cannot find" + render_plugin + " plugin."
            return None

        # 1. use roughness instead of glossiness
        # 2. reflection to White
        # 3. use tangent space normal mode
        setAttr("%s.useRoughness" % current_shader, 1)
        setAttr("%s.reflectionColor" % current_shader, 1, 1, 1, type="double3")
        setAttr("%s.bumpMapType" % current_shader, 1)

    elif render_plugin == "Renderman_PxrDisney":
        setAttr("%s.specular" % current_shader, 1)

    elif render_plugin == "RedShift":
        setAttr("%s.%s" % (current_shader, "refl_fresnel_mode"), 2)  # metalness workflow

    update_textures(current_shader, channel_dict, render_plugin, current_sg)

    select(target_obj_list)
    if len(target_obj_list) == 0:
        print "=== SP to Maya Sync Finished ==="
        return None
    result=confirmDialog(title='Confirm',
                         message='     Update Material Network for:     \n     %s?' % (ls(sl=1)[0]),
                         button =['Yes', 'No'], defaultButton='Yes',
                         cancelButton='No',
                         dismissString='No')
    if result == 'No':
        print "material update abort"
        print "=== SP to Maya Sync Finished ==="
        return None
    sets(target_obj_list, forceElement=current_sg)
    print "=== SP to Maya Sync Finished ==="


def update_textures(current_shader, channel_dict, render_plugin, current_sg):
    channel_dict = json.loads(channel_dict)
    # create file texture node
    for param_name in channel_dict:
        tokens = channel_dict[param_name][3]
        if len(tokens) < 4:
            continue  # skip if the textInput is empty or too short

        output_type= channel_dict[param_name][0]
        texture_path = channel_dict[param_name][1]
        texture_color_space = channel_dict[param_name][2]

        texture_filename = os.path.basename(texture_path).replace("1001", "\d\d\d\d")
        texture_folder = os.path.dirname(texture_path)
        texture_exists = None
        for f in os.listdir(texture_folder):
            texture_exists = re.search(texture_filename, f)
            if texture_exists:
                break

        if texture_exists is None:
            continue  # skip if no texture for current channel
        current_node = current_shader
        utils_node = current_shader + '_' + param_name
        print "start updating "+param_name

        if pm.objExists(utils_node):
            print 'update node'
            # if node exists, update texture path only
            file_node = update_file(0, utils_node, utils_node+'_p2d', texture_path, texture_color_space, render_plugin)

        elif param_name == 'aiNormal':
            normal_node = shadingNode('aiNormalMap', name=utils_node, asUtility=1, skipSelect=1)
            connectAttr('%s.outValue' % normal_node, '%s.normalCamera' % current_node)
            current_node = normal_node
            param_name = 'input'
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, texture_color_space, render_plugin)

        elif param_name == 'rsNormal':
            file_node = shadingNode('RedshiftNormalMap', name=utils_node, asUtility=1,skipSelect=1)
            setAttr("%s.tex0" % file_node, texture_path.replace('1001', '<UDIM>'), type="string")
            output_type = 'outDisplacementVector'
            param_name = 'bump_input'
        
        elif param_name == 'pxrNormal':
            file_node = shadingNode('PxrNormalMap', name=utils_node, asTexture=1, skipSelect=1)
            setAttr("%s.filename"%file_node, texture_path.replace("1001", "_MAPID_"), type="string")
            setAttr("%s.atlasStyle"%file_node, 1)
            output_type = 'resultN'
            param_name = 'bumpNormal'

        elif param_name == 'vrayNormal':
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, texture_color_space, render_plugin)
            output_type = 'outColor'
            param_name = 'bumpMap'
        
        elif param_name == 'displacement':
            print 'disp'
            disp_node = shadingNode('displacementShader', name=utils_node+"Node", asUtility=1, skipSelect=1)
            connectAttr('%s.displacement' % (disp_node), '%s.displacementShader' % current_sg)
            current_node = disp_node
            param_name = 'displacement'
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, texture_color_space, render_plugin)
            if render_plugin == "Renderman_PxrDisney":
                output_type = "resultR"

        elif render_plugin == "Renderman_PxrDisney":
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, texture_color_space, render_plugin)
            if output_type == "outColor":
                output_type = "resultRGB"
                setAttr("%s.linearize" % file_node, 1)
            else:
                output_type = "resultR"
        else:
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, texture_color_space, render_plugin)

        try:
            connectAttr('%s.%s' % (file_node, output_type), '%s.%s' % (current_node, param_name))
        except:
            pass


def update_file(create_file, file_name, p2d_name, texture_path, texture_color_space, render_plugin):
    if create_file == 1 and render_plugin != "Renderman_PxrDisney":
        # create file and place2d
        tex = pm.shadingNode('file', name=file_name, asTexture=True, isColorManaged=True)   
        if not pm.objExists(p2d_name):
            pm.shadingNode('place2dTexture', name=p2d_name, asUtility=True)
        p2d = pm.PyNode(p2d_name)
        tex.filterType.set(0)
        pm.connectAttr(p2d.outUV, tex.uvCoord)
        pm.connectAttr(p2d.outUvFilterSize, tex.uvFilterSize)
        pm.connectAttr(p2d.vertexCameraOne, tex.vertexCameraOne)
        pm.connectAttr(p2d.vertexUvOne, tex.vertexUvOne)
        pm.connectAttr(p2d.vertexUvThree, tex.vertexUvThree)
        pm.connectAttr(p2d.vertexUvTwo, tex.vertexUvTwo)
        pm.connectAttr(p2d.coverage, tex.coverage)
        pm.connectAttr(p2d.mirrorU, tex.mirrorU)
        pm.connectAttr(p2d.mirrorV, tex.mirrorV)
        pm.connectAttr(p2d.noiseUV, tex.noiseUV)
        pm.connectAttr(p2d.offset, tex.offset)
        pm.connectAttr(p2d.repeatUV, tex.repeatUV)
        pm.connectAttr(p2d.rotateFrame, tex.rotateFrame)
        pm.connectAttr(p2d.rotateUV, tex.rotateUV)
        pm.connectAttr(p2d.stagger, tex.stagger)
        pm.connectAttr(p2d.translateFrame, tex.translateFrame)
        pm.connectAttr(p2d.wrapU, tex.wrapU)
        pm.connectAttr(p2d.wrapV, tex.wrapV)
    elif create_file == 1 and render_plugin =="Renderman_PxrDisney":
        # create pxrTexture
        tex = pm.shadingNode('PxrTexture', name=file_name, asTexture=True)
        pm.setAttr(tex.atlasStyle, 1)
    else:
        # node exists
        tex = pm.PyNode(file_name)


    if render_plugin == "Renderman_PxrDisney":
        pm.setAttr(tex.filename, texture_path.replace("1001", "_MAPID_"))
        pm.setAttr(tex.atlasStyle, 1)
        if texture_color_space == "sRGB":
            pm.setAttr(tex.linearize, 1)
    elif render_plugin == "RedShift" and "rsNormal" in tex:
        pm.setAttr(tex.tex0, texture_path.replace('1001', '<UDIM>'), type="string")
    else:
        try:
            pm.setAttr(tex.fileTextureName, texture_path)
            pm.setAttr(tex.colorSpace, texture_color_space)
            pm.setAttr(tex.alphaIsLuminance, 1)
            pm.setAttr(tex.uvTilingMode, 3)
        except:
            pass

    print "finished updating " + file_name
    return tex
