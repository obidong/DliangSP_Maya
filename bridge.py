# coding: utf-8
from maya.cmds import*
import pymel.core as pm
import json, os, re

render_plugin_dict = {"Arnold": "aiStandardSurface", "VRay": "VRayMtl", "Renderman_PxrDisney": "PxrDisney", "RedShift": "RedshiftMaterial"}


def run(material_name, channel_dict, render_plugin):

    """
    material_name: name of the material
    channel_dict: {"basecolor":["E:/test/sword_BaseColor.$textureSet.tif","baseColor"],
    "displacement":["E:/test/sword_Displacement.$textureSet.tif","DISPLACEMENT"],
    "user0":["E:/test/sword_wetMask.$textureSet.tif","base"]}
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
    current_shader = None
    current_sg = None
    print "=== Start Creating %s Network ===" % render_plugin
    if render_plugin == "Arnold":
        print "==== Arnold ===="
        if not pluginInfo("mtoa", q=1, l=1):
            try:
                loadPlugin('mtoa')
            except:
                print "Cannot find " + render_plugin + " plugin."
                return None
        # create a shader and assign to selection
        current_shader = shadingNode(render_plugin_dict[render_plugin], name=material_name, asShader=1, skipSelect=1)
        current_sg = sets(renderable=True, noSurfaceShader=True, empty=1, name=current_shader+"SG")
        connectAttr("%s.outColor" % current_shader, "%s.surfaceShader" % current_sg)

    if render_plugin == "VRay":
        print "==== VRay ===="
        if not pluginInfo("vrayformaya", q=1, l=1):
            try:
                loadPlugin('vrayformaya')
            except:
                print "Cannot find " + render_plugin + " plugin."
                return None
        # create a shader and assign to selection
        current_shader = shadingNode(render_plugin_dict[render_plugin], name=material_name, asShader=1, skipSelect=1)
        current_sg = sets(renderable=True, noSurfaceShader=True, empty=1, name=current_shader+"SG")
        connectAttr("%s.outColor" % current_shader, "%s.surfaceShader" % current_sg)
        # 1. use roughness instead of glossiness
        # 2. reflection to White
        # 3. use tangent space normal mode
        setAttr("%s.useRoughness" % current_shader, 1)
        setAttr("%s.reflectionColor" % current_shader, 1, 1, 1, type="double3")
        setAttr("%s.bumpMapType" % current_shader, 1)

    elif render_plugin == "Renderman_PxrDisney":
        print "==== Renderman PxrDisney ===="
        if not pluginInfo("RenderMan_for_Maya", q=1, l=1):
            try:
                loadPlugin('RenderMan_for_Maya')
            except:
                print "Cannot find " + "Renderman" + " plugin."
                return None
        # create a shader and assign to selection
        current_shader = shadingNode(render_plugin_dict[render_plugin], name=material_name, asShader=1, skipSelect=1)
        current_sg = sets(renderable=True, noSurfaceShader=True, empty=1, name=current_shader+"SG")
        connectAttr("%s.outColor" % current_shader, "%s.surfaceShader" % current_sg)
        setAttr("%s.specular" % current_shader, 1)

    elif render_plugin == "RedShift":
        print "==== Renderman PxrDisney ===="
        if not pluginInfo("redshift4maya", q=1, l=1):
            try:
                loadPlugin('redshift4maya')
            except:
                print "Cannot find " + render_plugin + " plugin."
                return None
        # create a shader and assign to selection
        current_shader = shadingNode(render_plugin_dict[render_plugin], name=material_name, asShader=1, skipSelect=1)
        current_sg = sets(renderable=True, noSurfaceShader=True, empty=1, name=current_shader+"SG")
        connectAttr("%s.outColor" % current_shader, "%s.surfaceShader" % current_sg)
        setAttr("%s.%s" % (current_shader, "refl_fresnel_mode"), 2)  # metalness workflow

    update_textures(current_shader, channel_dict, render_plugin, current_sg)

    select(target_obj_list)
    if len(target_obj_list) == 0:
        print "=== SP to Maya Sync Finished ==="
        return None
    result = confirmDialog(title='Confirm',
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
    for channel in channel_dict:
        texture_path = channel_dict[channel][0]
        param_name = channel_dict[channel][1]
        if len(param_name)<4:
            continue
        output_type = "outColor"
        current_node = current_shader
        utils_node = current_shader + '_' + param_name
        print "start updating "+param_name

        if pm.objExists(utils_node):
            print 'update node'
            # if node exists, update texture path only
            file_node = update_file(0, utils_node, utils_node+'_p2d', texture_path, render_plugin)

        elif param_name == 'NORMAL' and render_plugin == "Arnold":
            normal_node = shadingNode('aiNormalMap', name=utils_node, asUtility=1, skipSelect=1)
            connectAttr('%s.outValue' % normal_node, '%s.normalCamera' % current_node)
            current_node = normal_node
            param_name = 'input'
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, render_plugin)

        elif param_name == 'NORMAL' and render_plugin == "RedShift":
            file_node = shadingNode('RedshiftNormalMap', name=utils_node, asUtility=1,skipSelect=1)
            setAttr("%s.tex0" % file_node, texture_path.replace('$textureSet', '<UDIM>'), type="string")
            output_type = 'outDisplacementVector'
            param_name = 'bump_input'
        
        elif param_name == 'NORMAL'and render_plugin == "Renderman_PxrDisney":
            file_node = shadingNode('PxrNormalMap', name=utils_node, asTexture=1, skipSelect=1)
            setAttr("%s.filename"%file_node, texture_path.replace("$textureSet", "_MAPID_"), type="string")
            setAttr("%s.atlasStyle"%file_node, 1)
            output_type = 'resultN'
            param_name = 'bumpNormal'

        elif param_name == 'NORMAL' and render_plugin == "VRay":
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, render_plugin)
            output_type = 'outColor'
            param_name = 'bumpMap'
        
        elif param_name == 'DISPLACEMENT':
            disp_node = shadingNode('displacementShader', name=utils_node+"Node", asUtility=1, skipSelect=1)
            connectAttr('%s.displacement' % (disp_node), '%s.displacementShader' % current_sg)
            current_node = disp_node
            param_name = 'displacement'
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, render_plugin)
            if render_plugin == "Renderman_PxrDisney":
                output_type = "resultR"

        elif render_plugin == "Renderman_PxrDisney":
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, render_plugin)
            output_type = "resultRGB"

        else:
            file_node = update_file(1, utils_node, utils_node+'_p2d', texture_path, render_plugin)

        print "connect %s.%s to %s.%s"%(file_node, output_type, current_node, param_name)
        if output_type == "outColor":
            print "connect %s.%s to %s.%s"%(file_node, output_type , current_node, param_name)
            try:
                connectAttr('%s.%s' % (file_node, "outColor"), '%s.%s' % (current_node, param_name))
            except:
                connectAttr('%s.%s' % (file_node, "outAlpha"), '%s.%s' % (current_node, param_name))
        elif output_type == "resultRGB":
            print "connect %s.%s to %s.%s"%(file_node, output_type , current_node, param_name)
            try:
                connectAttr('%s.%s' % (file_node, "resultRGB"), '%s.%s' % (current_node, param_name))
            except:
                connectAttr('%s.%s' % (file_node, "resultR"), '%s.%s' % (current_node, param_name))
        else:
            print "connect %s.%s to %s.%s"%(file_node, output_type , current_node, param_name)
            try:
                connectAttr('%s.%s' % (file_node, output_type), '%s.%s' % (current_node, param_name))
            except:
                pass


def update_file(create_file, file_name, p2d_name, texture_path, render_plugin):
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
        pm.setAttr(tex.filename, texture_path.replace("$textureSet", "_MAPID_"))
        pm.setAttr(tex.atlasStyle, 1)

    elif render_plugin == "RedShift" and "rsNormal" in tex:
        pm.setAttr(tex.tex0, texture_path.replace('$textureSet', '<UDIM>'), type="string")
    else:
        try:
            pm.setAttr(tex.fileTextureName, texture_path.replace('$textureSet', '<UDIM>'))
            pm.setAttr(tex.alphaIsLuminance, 1)
            pm.setAttr(tex.uvTilingMode, 3)
        except:
            pass

    print "finished updating " + file_name
    return tex
