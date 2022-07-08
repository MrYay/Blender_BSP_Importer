# ----------------------------------------------------------------------------#
# TODO:  refactor loading bsp files and md3 files, right now its a mess o.O
# TODO:  Fix reimporting model when only the zoffset is different
#       check if model already loaded, make a copy of it, replace all the
#       material names with new zoffset
# ----------------------------------------------------------------------------#

import imp

if "bpy" not in locals():
    import bpy

if "ImportHelper" not in locals():
    from bpy_extras.io_utils import ImportHelper
if "ExportHelper" not in locals():
    from bpy_extras.io_utils import ExportHelper

if "BspHelper" in locals():
    imp.reload(BspHelper)
else:
    from . import BspHelper

if "Entities" in locals():
    imp.reload(Entities)
else:
    from . import Entities

if "MD3" in locals():
    imp.reload(MD3)
else:
    from . import MD3

if "TAN" in locals():
    imp.reload(TAN)
else:
    from . import TAN

if "QuakeShader" in locals():
    imp.reload(QuakeShader)
else:
    from . import QuakeShader

if "QuakeLight" in locals():
    imp.reload(QuakeLight)
else:
    from . import QuakeLight

if "StringProperty" not in locals():
    from bpy.props import StringProperty

if "BoolProperty" not in locals():
    from bpy.props import BoolProperty

if "EnumProperty" not in locals():
    from bpy.props import EnumProperty

if "IntProperty" not in locals():
    from bpy.props import IntProperty

if "PropertyGroup" not in locals():
    from bpy.types import PropertyGroup

from .IDTech3Lib.ID3VFS import Q3VFS

if "os" not in locals():
    import os

if "BlenderBSP" in locals():
    imp.reload(BlenderBSP)
else:
    from . import BlenderBSP

if "Import_Settings" not in locals():
    from .IDTech3Lib.BspImportSettings import Import_Settings

if "Preset" not in locals():
    from .IDTech3Lib.BspImportSettings import Preset

if "SURFACE_TYPES" not in locals():
    from .IDTech3Lib.BspImportSettings import SURFACE_TYPE

from .IDTech3Lib.ID3Brushes import parse_brush
from .IDTech3Lib import MAP


class Import_ID3_BSP(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.id3_bsp"
    bl_label = "Import ID3 engine BSP (.bsp)"
    filename_ext = ".bsp"
    filter_glob: StringProperty(default="*.bsp", options={'HIDDEN'})

    filepath: StringProperty(
        name="File Path",
        description="File path used for importing the BSP file",
        maxlen=1024,
        default="")
    preset: EnumProperty(
        name="Import preset",
        description="You can select wether you want to import a bsp for "
        "editing, rendering, or previewing.",
        default=Preset.PREVIEW.value,
        items=[
            (Preset.PREVIEW.value, "Preview",
             "Builds eevee shaders, imports all misc_model_statics "
             "when available", 0),
            (Preset.EDITIING.value, "Entity Editing",
             "Builds eevee shaders, imports all entitys, enables "
             "entitiy modding", 1),
            (Preset.RENDERING.value, "Rendering",
             "Builds cycles shaders, only imports visable enities", 2),
            (Preset.BRUSHES.value, "Brushes",
             "Imports all Brushes", 3),
            (Preset.SHADOW_BRUSHES.value, "Shadow Brushes", "Imports "
             "Brushes as shadow casters", 4),
        ])
    subdivisions: IntProperty(
        name="Patch subdivisions",
        description="How often a patch is subdivided at import",
        default=2)
    min_atlas_size: EnumProperty(
        name="Minimum Lightmap atlas size",
        description="Sets the minimum lightmap atlas size",
        default='128',
        items=[
            ('128', "128", "128x128", 128),
            ('256', "256", "256x256", 256),
            ('512', "512", "512x512", 512),
            ('1024', "1024", "1024x1024", 1024),
            ('2048', "2048", "2048x2048", 2048),
        ])

    def execute(self, context):
        addon_name = __name__.split('.')[0]
        self.prefs = context.preferences.addons[addon_name].preferences

        fixed_base_path = self.prefs.base_path.replace("\\", "/")
        if not fixed_base_path.endswith('/'):
            fixed_base_path = fixed_base_path + '/'

        brush_imports = (
            Preset.BRUSHES.value,
            Preset.SHADOW_BRUSHES.value
        )
        surface_types = SURFACE_TYPE.BAD
        if self.preset in brush_imports:
            surface_types = SURFACE_TYPE.BRUSH | SURFACE_TYPE.PATCH
        else:
            surface_types = (SURFACE_TYPE.PLANAR |
                             SURFACE_TYPE.PATCH |
                             SURFACE_TYPE.TRISOUP |
                             SURFACE_TYPE.FAKK_TERRAIN)

        # trace some things like paths and lightmap size
        import_settings = Import_Settings(
            file=self.filepath.replace("\\", "/"),
            subdivisions=self.properties.subdivisions,
            min_atlas_size=(
                int(self.min_atlas_size),
                int(self.min_atlas_size)
                ),
            base_paths=[fixed_base_path],
            preset=self.properties.preset,
            front_culling=False,
            surface_types=surface_types
        )
        import_settings.log.append("----import_scene.ja_bsp----")

        # scene information
        context.scene.id_tech_3_importer_preset = self.preset
        if self.preset != "BRUSHES":
            context.scene.id_tech_3_bsp_path = self.filepath

        BlenderBSP.import_bsp_file(import_settings)

        # set world color to black to remove additional lighting
        background = context.scene.world.node_tree.nodes.get("Background")
        if background is not None:
            background.inputs[0].default_value = 0, 0, 0, 1
        else:
            import_settings.log.append(
                "WARNING: Could not set world color to black.")

        if self.properties.preset == "BRUSHES":
            context.scene.cycles.transparent_max_bounces = 32
        elif self.properties.preset == "RENDERING":
            context.scene.render.engine = "CYCLES"
        else:
            context.scene.render.engine = "BLENDER_EEVEE"

        for line in import_settings.log:
            print(line)

        return {'FINISHED'}


class Import_ID3_MD3(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.id3_md3"
    bl_label = "Import ID3 engine MD3 (.md3)"
    filename_ext = ".md3"
    filter_glob: StringProperty(default="*.md3", options={'HIDDEN'})

    filepath: StringProperty(
        name="File Path",
        description="File path used for importing the MD3 file",
        maxlen=1024,
        default="")
    import_tags: BoolProperty(
        name="Import Tags",
        description="Whether to import the md3 tags or not",
        default=True)
    preset: EnumProperty(
        name="Import preset",
        description="You can select wether you want to import a md3 per "
        "object or merged into one object.",
        default='MERGED',
        items=[
            ('MERGED', "Merged", "Merges all the md3 content into "
             "one object", 0),
            ('OBJECTS', "Objects", "Imports MD3 objects", 1),
        ])

    def execute(self, context):
        addon_name = __name__.split('.')[0]
        self.prefs = context.preferences.addons[addon_name].preferences

        fixed_base_path = self.prefs.base_path.replace("\\", "/")
        if not fixed_base_path.endswith('/'):
            fixed_base_path = fixed_base_path + '/'

        # trace some things like paths and lightmap size
        import_settings = Import_Settings()
        import_settings.base_paths.append(fixed_base_path)
        import_settings.bsp_name = ""
        import_settings.preset = "PREVIEW"

        # initialize virtual file system
        VFS = Q3VFS()
        for base_path in import_settings.base_paths:
            VFS.add_base(base_path)
        VFS.build_index()

        objs = MD3.ImportMD3Object(
            VFS,
            self.filepath.replace("\\", "/"),
            self.import_tags,
            self.preset == 'OBJECTS')
        QuakeShader.build_quake_shaders(VFS, import_settings, objs)

        return {'FINISHED'}


class Import_ID3_TIK(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.id3_tik"
    bl_label = "Import ID3 engine TIKK (.tik)"
    filename_ext = ".tik"
    filter_glob: StringProperty(default="*.tik", options={'HIDDEN'})

    filepath: StringProperty(
        name="File Path",
        description="File path used for importing the TIK file",
        maxlen=1024,
        default="")
    import_tags: BoolProperty(
        name="Import Tags",
        description="Whether to import the Tikk tags or not",
        default=True)
    preset: EnumProperty(
        name="Import preset",
        description="You can select wether you want to import a tik per "
        "object or merged into one object.",
        default='MERGED',
        items=[
            ('MERGED', "Merged", "Merges all the tik "
             "content into one object", 0),
            ('OBJECTS', "Objects", "Imports tik objects", 1),
        ])

    def execute(self, context):
        addon_name = __name__.split('.')[0]
        self.prefs = context.preferences.addons[addon_name].preferences

        fixed_base_path = self.prefs.base_path.replace("\\", "/")
        if not fixed_base_path.endswith('/'):
            fixed_base_path = fixed_base_path + '/'

        # trace some things like paths and lightmap size
        import_settings = Import_Settings()
        import_settings.base_paths.append(fixed_base_path)
        import_settings.bsp_name = ""
        import_settings.preset = "PREVIEW"

        # initialize virtual file system
        VFS = Q3VFS()
        for base_path in import_settings.base_paths:
            VFS.add_base(base_path)
        VFS.build_index()

        objs = TAN.ImportTIKObject(
            VFS,
            self.filepath.replace("\\", "/"),
            self.import_tags,
            self.preset == 'OBJECTS')
        QuakeShader.build_quake_shaders(VFS, import_settings, objs)

        return {'FINISHED'}


class Export_ID3_MD3(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.id3_md3"
    bl_label = "Export ID3 engine MD3 (.md3)"
    filename_ext = ".md3"
    filter_glob: StringProperty(default="*.md3", options={'HIDDEN'})

    filepath: StringProperty(
        name="File Path",
        description="File path used for exporting the MD3 file",
        maxlen=1024,
        default="")
    only_selected: BoolProperty(
        name="Export only selected",
        description="Exports only selected Objects",
        default=False)
    individual: BoolProperty(
        name="Local space coordinates",
        description="Uses every models local space coordinates instead of "
        "the world space")
    start_frame: IntProperty(
        name="Start Frame",
        description="First frame to export",
        default=0,
        min=0)
    end_frame: IntProperty(
        name="End Frame",
        description="Last frame to export",
        default=0,
        min=0)
    preset: EnumProperty(
        name="Surfaces",
        description="You can select wether you want to export per object "
        "or merged based on materials.",
        default='MATERIALS',
        items=[
            ('MATERIALS', "From Materials",
             "Merges surfaces based on materials. Supports multi "
             "material objects", 0),
            ('OBJECTS', "From Objects",
             "Simply export objects. There will be no optimization", 1),
        ])

    def execute(self, context):
        objects = context.scene.objects
        if self.only_selected:
            objects = context.selected_objects

        frame_list = range(self.start_frame, max(
            self.end_frame, self.start_frame) + 1)
        status = MD3.ExportMD3(
            self.filepath.replace("\\", "/"),
            objects,
            frame_list,
            self.individual,
            self.preset == 'MATERIALS')
        if status[0]:
            return {'FINISHED'}
        else:
            self.report({"ERROR"}, status[1])
            return {'CANCELLED'}


class Export_ID3_TIK(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.id3_tik"
    bl_label = "Export ID3 engine TIK (.tik)"
    filename_ext = ".tik"
    filter_glob: StringProperty(default="*.tik", options={'HIDDEN'})

    filepath: StringProperty(
        name="File Path",
        description="File path used for exporting the TIK file",
        maxlen=1024,
        default="")
    only_selected: BoolProperty(
        name="Export only selected",
        description="Exports only selected Objects",
        default=False)
    individual: BoolProperty(
        name="Local space coordinates",
        description="Uses every models local space coordinates instead of "
        "the world space")
    start_frame: IntProperty(
        name="Start Frame",
        description="First frame to export",
        default=0,
        min=0)
    end_frame: IntProperty(
        name="End Frame",
        description="Last frame to export",
        default=0,
        min=0)
    type: EnumProperty(
        name="Surface Type",
        description="You can select wether you want to export a tan "
        "model or skb model",
        default='TAN',
        items=[
            ('TAN', ".tan", "Exports a tan model", 0),
            ('SKB', ".skb", "Exports a skb model", 1),
        ])
    preset: EnumProperty(
        name="Surfaces",
        description="You can select wether you want to export per "
        "object or merged based on materials.",
        default='MATERIALS',
        items=[
            ('MATERIALS', "From Materials",
             "Merges surfaces based on materials. Supports "
             "multi material objects",
             0),
            ('OBJECTS', "From Objects",
             "Simply export objects. There will be no optimization",
             1),
        ])
    sub_path: bpy.props.StringProperty(
        name="Tan path",
        description="Where to save the tan file relative to the TIK file",
        default="",
        maxlen=2048,
    )

    def execute(self, context):
        objects = context.scene.objects
        if self.only_selected:
            objects = context.selected_objects

        fixed_subpath = self.sub_path.replace("\\", "/")
        if not fixed_subpath.endswith("/"):
            fixed_subpath += "/"
        if not fixed_subpath.startswith("/"):
            fixed_subpath = "/" + fixed_subpath

        frame_list = range(self.start_frame, max(
            self.end_frame, self.start_frame) + 1)
        if self.type == "TAN":
            status = TAN.ExportTIK_TAN(
                self.filepath.replace("\\", "/"),
                fixed_subpath,
                objects,
                frame_list,
                self.individual,
                self.preset == 'MATERIALS')
        else:
            self.report({"ERROR"}, "SKB exporting is not supported yet. :(")
        if status[0]:
            return {'FINISHED'}
        else:
            self.report({"ERROR"}, status[1])
            return {'CANCELLED'}


def menu_func_bsp_import(self, context):
    self.layout.operator(Import_ID3_BSP.bl_idname, text="ID3 BSP (.bsp)")


def menu_func_md3_import(self, context):
    self.layout.operator(Import_ID3_MD3.bl_idname, text="ID3 MD3 (.md3)")


def menu_func_tik_import(self, context):
    self.layout.operator(Import_ID3_TIK.bl_idname, text="ID3 TIK (.tik)")


def menu_func_md3_export(self, context):
    self.layout.operator(Export_ID3_MD3.bl_idname, text="ID3 MD3 (.md3)")


def menu_func_tik_export(self, context):
    self.layout.operator(Export_ID3_TIK.bl_idname, text="ID3 TIK (.tik)")


flag_mapping = {
    1: "b1",
    2: "b2",
    4: "b4",
    8: "b8",
    16: "b16",
    32: "b32",
    64: "b64",
    128: "b128",
    256: "b256",
    512: "b512",
}


class Del_property(bpy.types.Operator):
    bl_idname = "q3.del_property"
    bl_label = "Remove custom property"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}
    name: StringProperty()

    def execute(self, context):
        obj = bpy.context.active_object
        if self.name in obj:
            del obj[self.name]
            rna_ui = obj.get('_RNA_UI')
            if rna_ui is not None:
                del rna_ui[self.name]
        return {'FINISHED'}


type_matching = {"STRING": "NONE",
                 "COLOR": "COLOR_GAMMA",
                 "COLOR255": "COLOR_GAMMA",
                 "INT": "NONE",
                 "FLOAT": "NONE",
                 }
default_values = {"STRING": "",
                  "COLOR": [0.0, 0.0, 0.0],
                  "COLOR255": [0.0, 0.0, 0.0],
                  "INT": 0,
                  "FLOAT": 0.0,
                  }


class Add_property(bpy.types.Operator):
    bl_idname = "q3.add_property"
    bl_label = "Add custom property"
    bl_options = {"UNDO", "INTERNAL", "REGISTER"}
    name: StringProperty()

    def execute(self, context):
        ob = bpy.context.active_object
        key = self.name

        if key == "classname":
            ob["classname"] = ""
            return {'FINISHED'}

        Dict = Entities.Dict
        if self.name not in ob:
            default = ""

            rna_ui = ob.get('_RNA_UI')
            if rna_ui is None:
                ob['_RNA_UI'] = {}
                rna_ui = ob['_RNA_UI']

            descr_dict = {}
            if ob["classname"].lower() in Dict:
                if key.lower() in Dict[ob["classname"].lower()]["Keys"]:
                    if "Description" in Dict[
                            ob["classname"].lower()]["Keys"][key.lower()]:
                        descr_dict["description"] = Dict[ob["classname"].lower(
                        )]["Keys"][key.lower()]["Description"]
                    if "Type" in Dict[
                            ob["classname"].lower()]["Keys"][key.lower()]:
                        descr_dict["subtype"] = (
                            type_matching[Dict[ob["classname"].lower(
                            )]["Keys"][key.lower()]["Type"].upper()])
                        default = default_values[Dict[ob["classname"].lower(
                        )]["Keys"][key.lower()]["Type"].upper()]

            ob[self.name] = default
            rna_ui[key.lower()] = descr_dict
        return {'FINISHED'}


class Add_entity_definition(bpy.types.Operator):
    bl_idname = "q3.add_entity_definition"
    bl_label = "Update entity definition"
    bl_options = {"INTERNAL", "REGISTER"}
    name: StringProperty()

    def execute(self, context):
        obj = bpy.context.active_object
        new_entry = {"Color": [0.0, 0.5, 0.0],
                     "Mins": [-8, -8, -8],
                     "Maxs": [8, 8, 8],
                     "Model": "box",
                     "Describtion": "NOT DOCUMENTED YET",
                     "Spawnflags": {},
                     "Keys": {},
                     }

        Entities.Dict[self.name] = new_entry
        Entities.save_gamepack(
            Entities.Dict, context.scene.id_tech_3_settings.gamepack)
        return {'FINISHED'}


class Add_key_definition(bpy.types.Operator):
    bl_idname = "q3.add_key_definition"
    bl_label = "Update entity definition"
    bl_options = {"INTERNAL", "REGISTER"}
    name: StringProperty()

    def execute(self, context):
        obj = bpy.context.active_object

        if self.name != "":
            key = self.name
        else:
            scene = context.scene
            if "id_tech_3_settings" in scene:
                key = scene.id_tech_3_settings.new_prop_name
            else:
                print("Couldn't find new property name :(\n")
                return

        if "classname" in obj:
            classname = obj["classname"]
            if classname.lower() in Entities.Dict:
                if key not in Entities.Dict[classname.lower()]["Keys"]:
                    Entities.Dict[classname.lower()]["Keys"][key] = {
                        "Type": "STRING",
                        "Description": "NOT DOCUMENTED YET"}
                    Entities.save_gamepack(
                        Entities.Dict,
                        context.scene.id_tech_3_settings.gamepack)
        return {'FINISHED'}


type_save_matching = {"NONE": "STRING",
                      "COLOR_GAMMA": "COLOR",
                      "COLOR": "COLOR",
                      }


class Update_entity_definition(bpy.types.Operator):
    bl_idname = "q3.update_entity_definition"
    bl_label = "Update entity definition"
    bl_options = {"INTERNAL", "REGISTER"}
    name: StringProperty()

    def execute(self, context):
        obj = bpy.context.active_object

        rna_ui = obj.get('_RNA_UI')
        if rna_ui is None:
            obj['_RNA_UI'] = {}
            rna_ui = obj['_RNA_UI']

        if self.name in Entities.Dict:
            ent = Entities.Dict[self.name]
            for key in rna_ui.to_dict():
                if key in ent["Keys"] and key in rna_ui:
                    if "description" in rna_ui[key]:
                        ent["Keys"][key]["Description"] = (
                            rna_ui[key]["description"])
                    if "subtype" in rna_ui[key]:
                        ent["Keys"][key]["Type"] = (
                            type_save_matching[rna_ui[key]["subtype"]])

            Entities.save_gamepack(
                Entities.Dict, context.scene.id_tech_3_settings.gamepack)

        return {'FINISHED'}


def update_spawn_flag(self, context):
    obj = bpy.context.active_object
    if obj is None:
        return

    spawnflag = 0
    if obj.q3_dynamic_props.b1:
        spawnflag += 1
    if obj.q3_dynamic_props.b2:
        spawnflag += 2
    if obj.q3_dynamic_props.b4:
        spawnflag += 4
    if obj.q3_dynamic_props.b8:
        spawnflag += 8
    if obj.q3_dynamic_props.b16:
        spawnflag += 16
    if obj.q3_dynamic_props.b32:
        spawnflag += 32
    if obj.q3_dynamic_props.b64:
        spawnflag += 64
    if obj.q3_dynamic_props.b128:
        spawnflag += 128
    if obj.q3_dynamic_props.b256:
        spawnflag += 256
    if obj.q3_dynamic_props.b512:
        spawnflag += 512
    obj["spawnflags"] = spawnflag
    if spawnflag == 0:
        del obj["spawnflags"]


def get_empty_bsp_model_mesh():
    mesh = bpy.data.meshes.get("Empty_BSP_Model")
    if (mesh is None):
        ent_object = bpy.ops.mesh.primitive_cube_add(
            size=32.0, location=([0, 0, 0]))
        ent_object = bpy.context.object
        ent_object.name = "EntityBox"
        mesh = ent_object.data
        mesh.name = "Empty_BSP_Model"
        bpy.data.objects.remove(ent_object, do_unlink=True)
    return mesh


def get_empty_bsp_model_mat():
    mat = bpy.data.materials.get("Empty_BSP_Model")
    if (mat is None):
        mat = bpy.data.materials.new(name="Empty_BSP_Model")
        mat.use_nodes = True
        mat.blend_method = "CLIP"
        mat.shadow_method = "NONE"
        node = mat.node_tree.nodes["Principled BSDF"]
        node.inputs["Alpha"].default_value = 0.0
    return mat


def make_empty_bsp_model(context):
    mesh = get_empty_bsp_model_mesh()
    mat = get_empty_bsp_model_mat()
    ob = bpy.data.objects.new(name="Empty_BSP_Model", object_data=mesh.copy())
    ob.data.materials.append(mat)
    bpy.context.collection.objects.link(ob)
    return ob


def update_model(self, context):
    obj = bpy.context.active_object
    if obj is None:
        return

    dynamic_model = obj.q3_dynamic_props.model.split(".")[0]
    if (dynamic_model.startswith("*") and (
            dynamic_model not in bpy.data.meshes)) or (
            dynamic_model.strip(" \t\r\n") == ""):
        obj.data = get_empty_bsp_model_mesh()
        mat = get_empty_bsp_model_mat()
        obj["model"] = obj.q3_dynamic_props.model
        if mat.name not in obj.data.materials:
            obj.data.materials.append(mat)
        return

    orig_model = None
    if "model" in obj:
        orig_model = obj["model"][:]
        if not dynamic_model.startswith("*"):
            obj["model"] = dynamic_model + ".md3"
        else:
            obj["model"] = dynamic_model
        model_name = obj["model"]
    else:
        return

    if obj.data.name == dynamic_model:
        return

    model_name = model_name.replace("\\", "/").lower()
    if model_name.endswith(".md3"):
        model_name = model_name[:-len(".md3")]

    if not model_name.startswith("*"):
        mesh_name = guess_model_name(model_name)
    else:
        mesh_name = model_name
        obj["model"] = model_name

    if mesh_name in bpy.data.meshes:
        obj.data = bpy.data.meshes[mesh_name]
        obj.q3_dynamic_props.model = obj.data.name
    else:
        zoffset = 0
        if "zoffset" in obj:
            zoffset = int(obj["zoffset"])

        addon_name = __name__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences

        import_settings = ImportSettings()
        import_settings.base_path = prefs.base_path
        if not import_settings.base_path.endswith('/'):
            import_settings.base_path = import_settings.base_path + '/'
        import_settings.shader_dirs = "shaders/", "scripts/"
        import_settings.preset = 'PREVIEW'

        if model_name.startswith("models/"):
            model_name = import_settings.base_path + model_name
        # FIXME: Add VFS Support!
        mesh = MD3.ImportMD3(None, model_name + ".md3", zoffset)[0]
        if mesh is not None:
            obj.data = mesh
            obj.q3_dynamic_props.model = obj.data.name
            QuakeShader.build_quake_shaders(import_settings, [obj])
        elif orig_model is not None:
            obj["model"] = orig_model


def getChildren(obj):
    children = []
    for ob in bpy.data.objects:
        if ob.parent == obj:
            children.append(ob)
    return children


def update_model2(self, context):
    obj = bpy.context.active_object
    if obj is None:
        return

    if "model2" in obj:
        obj["model2"] = obj.q3_dynamic_props.model2.split(".")[0] + ".md3"
        model_name = obj["model2"]
    else:
        return

    model_name = model_name.replace("\\", "/").lower()
    if model_name.endswith(".md3"):
        model_name = model_name[:-len(".md3")]

    mesh_name = guess_model_name(model_name)

    children = getChildren(obj)
    if mesh_name.strip(" \t\r\n") == "" and len(children) > 0:
        for chil in children:
            bpy.data.objects.remove(chil, do_unlink=True)
        return

    if len(children) > 0:
        if children[0].data.name == obj.q3_dynamic_props.model2.split(".")[0]:
            return
    else:
        obj.parent = make_empty_bsp_model(context)
        obj.hide_select = True
        children = [obj]

    if mesh_name in bpy.data.meshes:
        children[0].data = bpy.data.meshes[mesh_name]
        obj.q3_dynamic_props.model2 = children[0].data.name
    else:
        zoffset = 0
        if "zoffset" in obj:
            zoffset = int(obj["zoffset"])

        addon_name = __name__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences

        import_settings = ImportSettings()
        import_settings.base_path = prefs.base_path
        if not import_settings.base_path.endswith('/'):
            import_settings.base_path = import_settings.base_path + '/'
        import_settings.shader_dirs = "shaders/", "scripts/"
        import_settings.preset = 'PREVIEW'

        if model_name.startswith("models/"):
            model_name = import_settings.base_path + model_name

        # FIXME: Add VFS Support!
        mesh = MD3.ImportMD3(None, model_name + ".md3", zoffset)[0]
        if mesh is not None:
            children[0].data = mesh
            obj.q3_dynamic_props.model2 = children[0].data.name
            QuakeShader.build_quake_shaders(import_settings, [children[0]])


# Properties like spawnflags and model
class DynamicProperties(PropertyGroup):
    b1: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    b2: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    b4: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    b8: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    b16: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    b32: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    b64: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    b128: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    b256: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    b512: BoolProperty(
        name="",
        default=False,
        update=update_spawn_flag
    )
    model: StringProperty(
        name="Model",
        default="EntityBox",
        update=update_model,
        subtype="FILE_PATH"
    )
    model2: StringProperty(
        name="Model2",
        default="EntityBox",
        update=update_model2,
        subtype="FILE_PATH"
    )

# Properties like spawnflags and model


class SceneProperties(PropertyGroup):

    def gamepack_list_cb(self, context):
        file_path = bpy.utils.script_paths("addons/import_bsp/gamepacks/")[0]
        gamepack_files = []

        try:
            gamepack_files = sorted(f for f in os.listdir(file_path)
                                    if f.endswith(".json"))
        except Exception as e:
            print('Could not open gamepack files ' + ", error: " + str(e))

        gamepack_list = [(gamepack, gamepack.split(".")[0], "")
                         for gamepack in sorted(gamepack_files)]

        return gamepack_list

    new_prop_name: StringProperty(
        name="New Property",
        default="",
    )
    gamepack: EnumProperty(
        items=gamepack_list_cb,
        name="Gamepack",
        description="List of available gamepacks"
    )

# Panels


class Q3_PT_ShaderPanel(bpy.types.Panel):
    bl_idname = "Q3_PT_shader_panel"
    bl_label = "Shaders"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Q3 Shaders"

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        row = layout.row()
        row.scale_y = 1.0
        row.operator("q3mapping.reload_preview_shader")
        row = layout.row()
        row.operator("q3mapping.reload_render_shader")
        layout.separator()

        lg_group = bpy.data.node_groups.get("LightGrid")
        if lg_group is not None:
            col = layout.column()
            if "Ambient light helper" in lg_group.nodes:
                ambient = lg_group.nodes["Ambient light helper"].outputs[0]
                col.prop(ambient, "default_value", text="Ambient light")
            if "Direct light helper" in lg_group.nodes:
                direct = lg_group.nodes["Direct light helper"].outputs[0]
                col.prop(direct, "default_value", text="Direct light")
            if "Light direction helper" in lg_group.nodes:
                vec = lg_group.nodes["Light direction helper"].outputs[0]
                col.prop(vec, "default_value", text="Light direction")

        emission_group = bpy.data.node_groups.get("EmissionScaleNode")
        if emission_group is not None:
            col = layout.column()
            if "Emission scale" in emission_group.nodes:
                scale = emission_group.nodes["Emission scale"].outputs[0]
                col.prop(scale, "default_value", text="Shader Emission Scale")
            if "Extra emission scale" in emission_group.nodes:
                scale = emission_group.nodes["Extra emission scale"].outputs[0]
                col.prop(scale, "default_value",
                         text="Extra Shader Emission Scale")


class Q3_PT_EntityPanel(bpy.types.Panel):
    bl_idname = "Q3_PT_entity_panel"
    bl_label = "Selected Entity"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Q3 Entities"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = bpy.context.active_object

        if obj is None:
            return

        # layout.prop(context.scene.id_tech_3_settings,"gamepack")
        layout.label(
            text=context.scene.id_tech_3_settings.gamepack.split(".")[0])

        if "classname" in obj:
            classname = obj["classname"].lower()
            layout.prop(obj, '["classname"]')
        else:
            op = layout.operator(
                "q3.add_property", text="Add classname").name = "classname"


class Q3_PT_PropertiesEntityPanel(bpy.types.Panel):
    bl_idname = "Q3_PT_properties_entity_panel"
    bl_parent_id = "Q3_PT_entity_panel"
    bl_label = "Entity Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Q3 Entities"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = bpy.context.active_object

        if obj is None:
            return

        filtered_keys = ["classname", "spawnflags",
                         "origin", "angles", "angle"]

        if "classname" in obj:
            classname = obj["classname"].lower()
            if classname in Entities.Dict:
                ent = Entities.Dict[classname]

                box = None
                # check all the flags
                for flag in ent["Spawnflags"].items():
                    if box is None:
                        box = layout.box()
                    box.prop(obj.q3_dynamic_props,
                             flag_mapping[flag[1]["Bit"]], text=flag[0])

                # now check all the keys
                supported = None
                unsupported = None
                keys = ent["Keys"]
                for prop in obj.keys():
                    # only show generic properties and filter
                    if prop.lower() not in filtered_keys and (
                            not hasattr(obj[prop], "to_dict")):
                        if prop.lower() == "model":
                            if supported is None:
                                supported = layout.box()
                            row = supported.row()
                            row.prop(obj.q3_dynamic_props,
                                     "model", text="model")
                            row.operator("q3.del_property",
                                         text="", icon="X").name = prop
                            continue
                        if prop.lower() == "model2":
                            if supported is None:
                                supported = layout.box()
                            row = supported.row()
                            row.prop(obj.q3_dynamic_props,
                                     "model2", text="model2")
                            row.operator("q3.del_property",
                                         text="", icon="X").name = prop
                            continue

                        if prop.lower() in keys:
                            if supported is None:
                                supported = layout.box()
                            row = supported.row()
                            row.prop(obj, '["' + prop + '"]')
                            row.operator("q3.del_property",
                                         text="", icon="X").name = prop
                        else:
                            if unsupported is None:
                                unsupported = layout.box()
                                unsupported.label(text="Unknown Properties:")
                            row = unsupported.row()
                            row.prop(obj, '["' + prop + '"]')
                            row.operator("q3.del_property",
                                         text="", icon="X").name = prop
                for key in keys:
                    test_key = obj.get(key.lower())
                    if test_key is None:
                        if supported is None:
                            supported = layout.box()
                        row = supported.row()
                        op = row.operator("q3.add_property",
                                          text="Add " + str(key)).name = key
            else:
                layout.label(text="Unknown entity")
                layout.label(
                    text='You can add it via "Edit Entity Definitions"')


class Q3_PT_DescribtionEntityPanel(bpy.types.Panel):
    bl_idname = "Q3_PT_describtion_entity_panel"
    bl_parent_id = "Q3_PT_entity_panel"
    bl_options = {"DEFAULT_CLOSED"}
    bl_label = "Entity Describtion"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Q3 Entities"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = bpy.context.active_object

        if obj is None:
            return

        if "classname" in obj:
            classname = obj["classname"].lower()
            if classname in Entities.Dict:
                ent = Entities.Dict[classname]
                for line in ent["Describtion"]:
                    layout.label(text=line)
            else:
                layout.label(text="Unknown entity")
                layout.label(
                    text='You can add it via "Edit Entity Definitions"')


class Q3_PT_EditEntityPanel(bpy.types.Panel):
    bl_idname = "Q3_PT_edit_entity_panel"
    bl_parent_id = "Q3_PT_entity_panel"
    bl_options = {"DEFAULT_CLOSED"}
    bl_label = "Edit Entity Definitions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Q3 Entities"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = bpy.context.active_object

        if obj is None:
            return

        filtered_keys = ["classname", "spawnflags",
                         "origin", "angles", "angle"]

        if "classname" in obj:
            classname = obj["classname"].lower()
            # classname in dictionary?
            if classname not in Entities.Dict:
                layout.operator(
                    "q3.add_entity_definition",
                    text="Add " + obj["classname"].lower() +
                         " to current Gamepack"
                         ).name = obj["classname"].lower()
            else:
                ent = Entities.Dict[classname]
                keys = ent["Keys"]
                for prop in obj.keys():
                    if prop.lower() not in filtered_keys and (
                            not hasattr(obj[prop], "to_dict")):
                        if prop.lower() not in keys:
                            op = layout.operator(
                                "q3.add_key_definition",
                                text="Add " + str(prop.lower()) +
                                     " to entity definition"
                                     ).name = prop.lower()

                row = layout.row()
                row.prop(context.scene.id_tech_3_settings, 'new_prop_name')
                row.operator("q3.add_key_definition",
                             text="", icon="PLUS").name = ""

                layout.separator()
                layout.operator("q3.update_entity_definition").name = classname


class ExportEnt(bpy.types.Operator, ExportHelper):
    bl_idname = "q3.export_ent"
    bl_label = "Export to .ent file"
    bl_options = {"INTERNAL", "REGISTER"}
    filename_ext = ".ent"
    filter_glob: StringProperty(default="*.ent", options={'HIDDEN'})
    filepath: bpy.props.StringProperty(
        name="File",
        description="Where to write the .ent file",
        maxlen=1024,
        default="")

    def execute(self, context):
        entities = Entities.GetEntityStringFromScene()

        f = open(self.filepath, "w")
        try:
            f.write(entities)
        except Exception:
            print("Failed writing: " + self.filepath)

        f.close()
        return {'FINISHED'}


class PatchBspEntities(bpy.types.Operator, ExportHelper):
    bl_idname = "q3.patch_bsp_ents"
    bl_label = "Patch entities in existing .bsp"
    bl_options = {"INTERNAL", "REGISTER"}
    filename_ext = ".bsp"
    filter_glob: StringProperty(default="*.bsp", options={'HIDDEN'})
    filepath: StringProperty(
        name="File",
        description="Which .bsp file to patch",
        maxlen=1024,
        default="")
    create_backup: BoolProperty(
        name="Append a suffix to the output file (don't "
        "overwrite original file)",
        default=True)

    def execute(self, context):

        bsp = BspClasses.BSP(self.filepath)

        # swap entity lump
        entities = Entities.GetEntityStringFromScene()
        bsp.lumps["entities"].data = [BspClasses.entity(
            [bytes(c, "ascii")]) for c in entities]

        # write bsp
        bsp_bytes = bsp.to_bytes()

        name = self.filepath
        if self.create_backup is True:
            name = name.replace(".bsp", "") + "_ent_patched.bsp"

        f = open(name, "wb")
        try:
            f.write(bsp_bytes)
        except Exception:
            print("Failed writing: " + name)

        f.close()
        return {'FINISHED'}


class PatchBspData(bpy.types.Operator, ExportHelper):
    bl_idname = "q3.patch_bsp_data"
    bl_label = "Patch data in existing .bsp"
    bl_options = {"INTERNAL", "REGISTER"}
    filename_ext = ".bsp"
    filter_glob: StringProperty(default="*.bsp", options={'HIDDEN'})
    filepath: StringProperty(
        name="File",
        description="Which .bsp file to patch",
        maxlen=1024,
        default="")
    only_selected: BoolProperty(name="Only selected objects", default=False)
    create_backup: BoolProperty(
        name="Append a suffix to filename (don't overwrite original file)",
        default=True)
    patch_lm_tcs: BoolProperty(name="Lightmap texture coordinates",
                               default=True)
    patch_tcs: BoolProperty(name="Texture coordinates", default=False)
    patch_normals: BoolProperty(name="Normals", default=False)

    patch_colors: BoolProperty(name="Vertex Colors", default=False)
    patch_lightgrid: BoolProperty(name="Light Grid", default=False)
    patch_lightmaps: BoolProperty(name="Lightmaps", default=True)
    lightmap_to_use: EnumProperty(
        name="Lightmap Atlas",
        description="Lightmap Atlas that will be used for patching",
        default='$lightmap_bake',
        items=[
            ('$lightmap_bake', "$lightmap_bake", "$lightmap_bake", 0),
            ('$lightmap', "$lightmap", "$lightmap", 1)])
    patch_external: BoolProperty(name="Save External Lightmaps", default=False)
    patch_external_flip: BoolProperty(
        name="Flip External Lightmaps",
        default=False)
    patch_empty_lm_lump: BoolProperty(
        name="Remove Lightmaps in BSP",
        default=False)
    patch_hdr: BoolProperty(
        name="HDR Lighting Export",
        default=False)
    lightmap_gamma: EnumProperty(
        name="Lightmap Gamma",
        description="Lightmap Gamma Correction",
        default='sRGB',
        items=[
            ('sRGB', "sRGB", "sRGB", 0),
            ('2.0', "2.0", "2.0", 1),
            ('4.0', "4.0", "4.0", 2)
        ])
    overbright_bits: EnumProperty(
        name="Overbright Bits",
        description="Overbright Bits",
        default='0',
        items=[
            ('0', "0", "0", 0),
            ('1', "1", "1", 1),
            ('2', "2", "2", 2)
        ])
    compensate: BoolProperty(name="Compensate", default=False)

    # TODO Shader lump + shader assignments
    def execute(self, context):
        class light_settings:
            pass
        light_settings = light_settings()
        light_settings.gamma = self.lightmap_gamma
        light_settings.overbright_bits = int(self.overbright_bits)
        light_settings.compensate = self.compensate
        light_settings.hdr = self.patch_hdr

        bsp = BspClasses.BSP(self.filepath)

        if self.only_selected:
            objs = [
                obj
                for obj in context.selected_objects
                if obj.type == "MESH"
            ]
        else:
            if bpy.app.version >= (2, 91, 0):
                objs = [obj for obj in context.scene.objects if obj.type ==
                        "MESH" and obj.data.attributes.get("BSP_VERT_INDEX") is not None]
            else:
                objs = [obj for obj in context.scene.objects if obj.type ==
                        "MESH" and obj.data.vertex_layers_int.get("BSP_VERT_INDEX") is not None]

        meshes = [obj.to_mesh() for obj in objs]
        for mesh in meshes:
            mesh.calc_normals_split()

        if self.patch_colors or self.patch_normals or self.patch_lm_tcs or self.patch_tcs:
            self.report({"INFO"}, "Storing Vertex Data...")
            # stores bsp vertex indices
            patched_vertices = {id: False for id in range(
                int(bsp.lumps["drawverts"].count))}
            lightmapped_vertices = {id: False for id in range(
                int(bsp.lumps["drawverts"].count))}
            patch_lighting_type = True
            for obj, mesh in zip(objs, meshes):
                if self.patch_lm_tcs:
                    group_map = {
                        group.name: group.index for group in obj.vertex_groups}
                    if "Lightmapped" not in group_map:
                        patch_lighting_type = False

                if bpy.app.version >= (2, 91, 0):
                    msh_bsp_vert_index_layer = mesh.attributes.get(
                        "BSP_VERT_INDEX")
                else:
                    msh_bsp_vert_index_layer = mesh.vertex_layers_int.get(
                        "BSP_VERT_INDEX")

                # check if its an imported bsp data set
                if msh_bsp_vert_index_layer is not None:
                    bsp_indices = msh_bsp_vert_index_layer

                    if self.patch_lm_tcs and patch_lighting_type:
                        # store all vertices that are lightmapped
                        for index in [bsp_indices.data[vertex.index].value
                                      for vertex in mesh.vertices
                                      if group_map["Lightmapped"] in
                                      [vg.group for vg in vertex.groups]]:
                            if index >= 0:
                                lightmapped_vertices[index] = True

                    # patch all vertices of this mesh
                    for poly in mesh.polygons:
                        for vertex, loop in zip(poly.vertices, poly.loop_indices):
                            # get the vertex position in the bsp file
                            bsp_vert_index = bsp_indices.data[vertex].value
                            if bsp_vert_index < 0:
                                continue
                            patched_vertices[bsp_vert_index] = True
                            bsp_vert = bsp.lumps["drawverts"].data[bsp_vert_index]
                            if self.patch_tcs:
                                bsp_vert.texcoord = mesh.uv_layers["UVMap"].data[loop].uv
                            if self.patch_lm_tcs:
                                bsp_vert.lm1coord = mesh.uv_layers["LightmapUV"].data[loop].uv
                                bsp_vert.lm1coord[0] = min(
                                    1.0, max(0.0, bsp_vert.lm1coord[0]))
                                bsp_vert.lm1coord[1] = min(
                                    1.0, max(0.0, bsp_vert.lm1coord[1]))
                                if bsp.lightmaps == 4:
                                    bsp_vert.lm2coord = mesh.uv_layers["LightmapUV2"].data[loop].uv
                                    bsp_vert.lm2coord[0] = min(
                                        1.0, max(0.0, bsp_vert.lm2coord[0]))
                                    bsp_vert.lm2coord[1] = min(
                                        1.0, max(0.0, bsp_vert.lm2coord[1]))
                                    bsp_vert.lm3coord = mesh.uv_layers["LightmapUV3"].data[loop].uv
                                    bsp_vert.lm3coord[0] = min(
                                        1.0, max(0.0, bsp_vert.lm3coord[0]))
                                    bsp_vert.lm3coord[1] = min(
                                        1.0, max(0.0, bsp_vert.lm3coord[1]))
                                    bsp_vert.lm4coord = mesh.uv_layers["LightmapUV4"].data[loop].uv
                                    bsp_vert.lm4coord[0] = min(
                                        1.0, max(0.0, bsp_vert.lm4coord[0]))
                                    bsp_vert.lm4coord[1] = min(
                                        1.0, max(0.0, bsp_vert.lm4coord[1]))
                            if self.patch_normals:
                                bsp_vert.normal = mesh.vertices[vertex].normal.copy(
                                )
                                if mesh.has_custom_normals:
                                    bsp_vert.normal = mesh.loops[loop].normal.copy(
                                    )
                            if self.patch_colors:
                                bsp_vert.color1 = mesh.vertex_colors["Color"].data[loop].color
                                bsp_vert.color1[3] = mesh.vertex_colors["Alpha"].data[loop].color[0]
                                if bsp.lightmaps == 4:
                                    bsp_vert.color2 = mesh.vertex_colors["Color2"].data[loop].color
                                    bsp_vert.color2[3] = mesh.vertex_colors["Alpha"].data[loop].color[1]
                                    bsp_vert.color3 = mesh.vertex_colors["Color3"].data[loop].color
                                    bsp_vert.color3[3] = mesh.vertex_colors["Alpha"].data[loop].color[2]
                                    bsp_vert.color4 = mesh.vertex_colors["Color4"].data[loop].color
                                    bsp_vert.color4[3] = mesh.vertex_colors["Alpha"].data[loop].color[3]
                else:
                    self.report({"ERROR"}, "Not a valid mesh for patching")
                    return {'CANCELLED'}

            self.report({"INFO"}, "Successful")

        if self.patch_lm_tcs or self.patch_tcs:
            self.report({"INFO"}, "Storing Texture Coordinates...")
            lightmap_size = bsp.lightmap_size
            packed_lightmap_size = [
                lightmap_size[0] *
                bpy.context.scene.id_tech_3_lightmaps_per_column,
                lightmap_size[1] *
                bpy.context.scene.id_tech_3_lightmaps_per_row]

            fixed_vertices = []
            # fix lightmap tcs and tcs, set lightmap ids
            for bsp_surf in bsp.lumps["surfaces"].data:
                # fix lightmap tcs and tcs for patches
                # unsmoothes tcs, so the game creates the same tcs we see here
                # in blender
                if bsp_surf.type == 2:
                    width = int(bsp_surf.patch_width-1)
                    height = int(bsp_surf.patch_height-1)
                    ctrlPoints = [[0 for x in range(bsp_surf.patch_width)] for y in range(
                        bsp_surf.patch_height)]
                    for i in range(bsp_surf.patch_width):
                        for j in range(bsp_surf.patch_height):
                            ctrlPoints[j][i] = (
                                bsp.lumps["drawverts"].data[
                                    bsp_surf.vertex +
                                    j*bsp_surf.patch_width + i])

                    for i in range(width+1):
                        for j in range(1, height, 2):
                            if self.patch_lm_tcs:
                                ctrlPoints[j][i].lm1coord[0] = (
                                    4.0 * ctrlPoints[j][i].lm1coord[0] - ctrlPoints[j+1][i].lm1coord[0] - ctrlPoints[j-1][i].lm1coord[0]) * 0.5
                                ctrlPoints[j][i].lm1coord[1] = (
                                    4.0 * ctrlPoints[j][i].lm1coord[1] - ctrlPoints[j+1][i].lm1coord[1] - ctrlPoints[j-1][i].lm1coord[1]) * 0.5
                                if bsp.lightmaps == 4:
                                    ctrlPoints[j][i].lm2coord[0] = (
                                        4.0 * ctrlPoints[j][i].lm2coord[0] - ctrlPoints[j+1][i].lm2coord[0] - ctrlPoints[j-1][i].lm2coord[0]) * 0.5
                                    ctrlPoints[j][i].lm2coord[1] = (
                                        4.0 * ctrlPoints[j][i].lm2coord[1] - ctrlPoints[j+1][i].lm2coord[1] - ctrlPoints[j-1][i].lm2coord[1]) * 0.5
                                    ctrlPoints[j][i].lm3coord[0] = (
                                        4.0 * ctrlPoints[j][i].lm3coord[0] - ctrlPoints[j+1][i].lm3coord[0] - ctrlPoints[j-1][i].lm3coord[0]) * 0.5
                                    ctrlPoints[j][i].lm3coord[1] = (
                                        4.0 * ctrlPoints[j][i].lm3coord[1] - ctrlPoints[j+1][i].lm3coord[1] - ctrlPoints[j-1][i].lm3coord[1]) * 0.5
                                    ctrlPoints[j][i].lm4coord[0] = (
                                        4.0 * ctrlPoints[j][i].lm4coord[0] - ctrlPoints[j+1][i].lm4coord[0] - ctrlPoints[j-1][i].lm4coord[0]) * 0.5
                                    ctrlPoints[j][i].lm4coord[1] = (
                                        4.0 * ctrlPoints[j][i].lm4coord[1] - ctrlPoints[j+1][i].lm4coord[1] - ctrlPoints[j-1][i].lm4coord[1]) * 0.5
                            if self.patch_tcs:
                                ctrlPoints[j][i].texcoord[0] = (
                                    4.0 * ctrlPoints[j][i].texcoord[0] - ctrlPoints[j+1][i].texcoord[0] - ctrlPoints[j-1][i].texcoord[0]) * 0.5
                                ctrlPoints[j][i].texcoord[1] = (
                                    4.0 * ctrlPoints[j][i].texcoord[1] - ctrlPoints[j+1][i].texcoord[1] - ctrlPoints[j-1][i].texcoord[1]) * 0.5
                    for j in range(height+1):
                        for i in range(1, width, 2):
                            if self.patch_lm_tcs:
                                ctrlPoints[j][i].lm1coord[0] = (
                                    4.0 * ctrlPoints[j][i].lm1coord[0] - ctrlPoints[j][i+1].lm1coord[0] - ctrlPoints[j][i-1].lm1coord[0]) * 0.5
                                ctrlPoints[j][i].lm1coord[1] = (
                                    4.0 * ctrlPoints[j][i].lm1coord[1] - ctrlPoints[j][i+1].lm1coord[1] - ctrlPoints[j][i-1].lm1coord[1]) * 0.5
                                if bsp.lightmaps == 4:
                                    ctrlPoints[j][i].lm2coord[0] = (
                                        4.0 * ctrlPoints[j][i].lm2coord[0] - ctrlPoints[j][i+1].lm2coord[0] - ctrlPoints[j][i-1].lm2coord[0]) * 0.5
                                    ctrlPoints[j][i].lm2coord[1] = (
                                        4.0 * ctrlPoints[j][i].lm2coord[1] - ctrlPoints[j][i+1].lm2coord[1] - ctrlPoints[j][i-1].lm2coord[1]) * 0.5
                                    ctrlPoints[j][i].lm3coord[0] = (
                                        4.0 * ctrlPoints[j][i].lm3coord[0] - ctrlPoints[j][i+1].lm3coord[0] - ctrlPoints[j][i-1].lm3coord[0]) * 0.5
                                    ctrlPoints[j][i].lm3coord[1] = (
                                        4.0 * ctrlPoints[j][i].lm3coord[1] - ctrlPoints[j][i+1].lm3coord[1] - ctrlPoints[j][i-1].lm3coord[1]) * 0.5
                                    ctrlPoints[j][i].lm4coord[0] = (
                                        4.0 * ctrlPoints[j][i].lm4coord[0] - ctrlPoints[j][i+1].lm4coord[0] - ctrlPoints[j][i-1].lm4coord[0]) * 0.5
                                    ctrlPoints[j][i].lm4coord[1] = (
                                        4.0 * ctrlPoints[j][i].lm4coord[1] - ctrlPoints[j][i+1].lm4coord[1] - ctrlPoints[j][i-1].lm4coord[1]) * 0.5
                            if self.patch_tcs:
                                ctrlPoints[j][i].texcoord[0] = (
                                    4.0 * ctrlPoints[j][i].texcoord[0] - ctrlPoints[j][i+1].texcoord[0] - ctrlPoints[j][i-1].texcoord[0]) * 0.5
                                ctrlPoints[j][i].texcoord[1] = (
                                    4.0 * ctrlPoints[j][i].texcoord[1] - ctrlPoints[j][i+1].texcoord[1] - ctrlPoints[j][i-1].texcoord[1]) * 0.5

                if self.patch_lm_tcs:
                    # set new lightmap ids
                    vertices = set()
                    lightmap_id = []
                    lightmap_id2 = []
                    lightmap_id3 = []
                    lightmap_id4 = []
                    if bsp_surf.type != 2:
                        for i in range(int(bsp_surf.n_indexes)):
                            bsp_vert_index = bsp_surf.vertex + \
                                bsp.lumps["drawindexes"].data[bsp_surf.index + i].offset
                            # only alter selected vertices
                            if patched_vertices[bsp_vert_index]:
                                vertices.add(bsp_vert_index)
                                bsp_vert = (
                                    bsp.lumps["drawverts"].data[bsp_vert_index])
                                if lightmapped_vertices[bsp_vert_index] and patch_lighting_type:
                                    lightmap_id.append(
                                        BspHelper.get_lm_id(
                                            bsp_vert.lm1coord,
                                            lightmap_size,
                                            packed_lightmap_size))
                                    if bsp.lightmaps == 4:
                                        lightmap_id2.append(
                                            BspHelper.get_lm_id(
                                                bsp_vert.lm2coord,
                                                lightmap_size,
                                                packed_lightmap_size))
                                        lightmap_id3.append(
                                            BspHelper.get_lm_id(
                                                bsp_vert.lm3coord,
                                                lightmap_size,
                                                packed_lightmap_size))
                                        lightmap_id4.append(
                                            BspHelper.get_lm_id(
                                                bsp_vert.lm4coord,
                                                lightmap_size,
                                                packed_lightmap_size))
                    else:
                        for i in range(bsp_surf.patch_width):
                            for j in range(bsp_surf.patch_height):
                                bsp_vert_index = (
                                    bsp_surf.vertex+j*bsp_surf.patch_width+i)
                                if patched_vertices[bsp_vert_index]:
                                    vertices.add(bsp_vert_index)
                                    bsp_vert = bsp.lumps["drawverts"].data[bsp_vert_index]
                                    if lightmapped_vertices[bsp_vert_index] and patch_lighting_type:
                                        lightmap_id.append(
                                            BspHelper.get_lm_id(
                                                bsp_vert.lm1coord,
                                                lightmap_size,
                                                packed_lightmap_size))
                                        if bsp.lightmaps == 4:
                                            lightmap_id2.append(
                                                BspHelper.get_lm_id(
                                                    bsp_vert.lm2coord,
                                                    lightmap_size,
                                                    packed_lightmap_size))
                                            lightmap_id3.append(
                                                BspHelper.get_lm_id(
                                                    bsp_vert.lm3coord,
                                                    lightmap_size,
                                                    packed_lightmap_size))
                                            lightmap_id4.append(
                                                BspHelper.get_lm_id(
                                                    bsp_vert.lm4coord,
                                                    lightmap_size,
                                                    packed_lightmap_size))

                    if len(vertices) > 0:
                        if len(lightmap_id) > 0:
                            current_lm_id = lightmap_id[0]
                            for i in lightmap_id:
                                if i != current_lm_id:
                                    self.report(
                                        {"WARNING"}, "Warning: Surface found "
                                        "with multiple lightmap assignments "
                                        "which is not supported! Surface will "
                                        "be stored as vertex lit!")
                                    lightmap_id[0] = -3
                                    break
                            if bsp.lightmaps == 4:
                                current_lm_id = lightmap_id2[0]
                                for i in lightmap_id2:
                                    if i != current_lm_id:
                                        lightmap_id2[0] = -3
                                        break
                                current_lm_id = lightmap_id3[0]
                                for i in lightmap_id3:
                                    if i != current_lm_id:
                                        lightmap_id3[0] = -3
                                        break
                                current_lm_id = lightmap_id4[0]
                                for i in lightmap_id4:
                                    if i != current_lm_id:
                                        lightmap_id4[0] = -3
                                        break

                            if patch_lighting_type or (
                                    bsp_surf.lm_indexes[0] >= 0):
                                # bsp_surf.type = 1 #force using lightmaps
                                # for surfaces with less than 64 verticies
                                bsp_surf.lm_indexes[0] = lightmap_id[0]
                                if bsp.lightmaps == 4:
                                    bsp_surf.lm_indexes[1] = lightmap_id2[0]
                                    bsp_surf.lm_indexes[2] = lightmap_id3[0]
                                    bsp_surf.lm_indexes[3] = lightmap_id4[0]

                        # unpack lightmap tcs
                        for i in vertices:
                            bsp_vert = bsp.lumps["drawverts"].data[i]
                            BspHelper.unpack_lm_tc(
                                bsp_vert.lm1coord,
                                lightmap_size,
                                packed_lightmap_size)
                            if bsp.lightmaps == 4:
                                BspHelper.unpack_lm_tc(
                                    bsp_vert.lm2coord,
                                    lightmap_size,
                                    packed_lightmap_size)
                                BspHelper.unpack_lm_tc(
                                    bsp_vert.lm3coord,
                                    lightmap_size,
                                    packed_lightmap_size)
                                BspHelper.unpack_lm_tc(
                                    bsp_vert.lm4coord,
                                    lightmap_size,
                                    packed_lightmap_size)
            self.report({"INFO"}, "Successful")
        # get number of lightmaps
        n_lightmaps = 0
        for bsp_surf in bsp.lumps["surfaces"].data:
            # handle lightmap ids with lightstyles
            for i in range(bsp.lightmaps):
                if bsp_surf.lm_indexes[i] > n_lightmaps:
                    n_lightmaps = bsp_surf.lm_indexes[i]

        # store lightmaps
        if self.patch_lightmaps:
            lightmap_image = bpy.data.images.get(self.lightmap_to_use)
            if lightmap_image is None:
                self.report(
                    {"ERROR"}, "Could not find selected lightmap atlas")
                return {'CANCELLED'}
            self.report({"INFO"}, "Storing Lightmaps...")
            success, message = QuakeLight.storeLighmaps(
                bsp,
                lightmap_image,
                n_lightmaps + 1,
                light_settings,
                not self.patch_external,
                self.patch_external_flip)
            self.report({"INFO"} if success else {"ERROR"}, message)

        # clear lightmap lump
        if self.patch_empty_lm_lump:
            bsp.lumps["lightmaps"].clear()

        # store lightgrid
        if self.patch_lightgrid:
            self.report({"INFO"}, "Storing Lightgrid...")
            success, message = QuakeLight.storeLightgrid(bsp, light_settings)
            self.report({"INFO"} if success else {"ERROR"}, message)

        # store vertex colors
        if self.patch_colors:
            self.report({"INFO"}, "Storing Vertex Colors...")
            success, message = QuakeLight.storeVertexColors(
                bsp, objs, light_settings, self.patch_colors)
            self.report({"INFO"} if success else {"ERROR"}, message)

        # write bsp
        bsp_bytes = bsp.to_bytes()

        name = self.filepath
        if self.create_backup is True:
            name = name.replace(".bsp", "") + "_data_patched.bsp"

        f = open(name, "wb")
        try:
            f.write(bsp_bytes)
        except Exception:
            self.report({"ERROR"}, "Failed writing: " + name)
            return {'CANCELLED'}
        f.close()

        return {'FINISHED'}


class Prepare_Lightmap_Baking(bpy.types.Operator):
    bl_idname = "q3.prepare_lm_baking"
    bl_label = "Prepare Lightmap Baking"
    bl_options = {"INTERNAL", "REGISTER"}

    def execute(self, context):
        bpy.context.view_layer.objects.active = None
        for obj in bpy.context.scene.objects:
            obj.select_set(False)
            if obj.type == "MESH":
                mesh = obj.data
                if mesh.name.startswith("*") and (
                        obj.name in bpy.context.view_layer.objects):
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)
                    if "LightmapUV" in mesh.uv_layers:
                        mesh.uv_layers["LightmapUV"].active = True

        for mat in bpy.data.materials:
            node_tree = mat.node_tree
            if node_tree is None:
                continue

            nodes = node_tree.nodes
            for node in nodes:
                node.select = False

            if "Baking Image" in nodes:
                nodes["Baking Image"].select = True
                nodes.active = nodes["Baking Image"]

        return {'FINISHED'}


class Store_Vertex_Colors(bpy.types.Operator):
    bl_idname = "q3.store_vertex_colors"
    bl_label = "Store Vertex Colors"
    bl_options = {"INTERNAL", "REGISTER"}

    def execute(self, context):
        objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        # TODO: handle lightsyles
        success, message = QuakeLight.bake_uv_to_vc(
            objs, "LightmapUV", "Color")
        if not success:
            self.report({"ERROR"}, message)
            return {'CANCELLED'}

        return {'FINISHED'}


class Create_Lightgrid(bpy.types.Operator):
    bl_idname = "q3.create_lightgrid"
    bl_label = "Create Lightgrid"
    bl_options = {"INTERNAL", "REGISTER"}

    def execute(self, context):
        if QuakeLight.create_lightgrid() is False:
            self.report({"ERROR"}, "BspInfo Node Group not found")
            return {'CANCELLED'}

        return {'FINISHED'}


class Convert_Baked_Lightgrid(bpy.types.Operator):
    bl_idname = "q3.convert_baked_lightgrid"
    bl_label = "Convert Baked Lightgrid"
    bl_options = {"INTERNAL", "REGISTER"}

    def execute(self, context):
        if QuakeLight.createLightGridTextures() is False:
            self.report({"ERROR"}, "Couldn't convert baked lightgrid textures")
            return {'CANCELLED'}

        return {'FINISHED'}


def pack_image(name):
    image = bpy.data.images.get(name)
    if image is not None:
        if image.packed_file is None or image.is_dirty:
            image.pack()
        return True
    return False


class Pack_Lightmap_Images(bpy.types.Operator):
    bl_idname = "q3.pack_lightmap_images"
    bl_label = "Pack Lightmap Images"
    bl_options = {"INTERNAL", "REGISTER"}

    def execute(self, context):
        images = ["$lightmap_bake", "$vertmap_bake"]
        for image in images:
            if not pack_image(image):
                error = "Couldn't pack " + image + " image"
                self.report({"ERROR"}, error)
        return {'FINISHED'}


class Pack_Lightgrid_Images(bpy.types.Operator):
    bl_idname = "q3.pack_lightgrid_images"
    bl_label = "Pack Lightgrid Images"
    bl_options = {"INTERNAL", "REGISTER"}

    def execute(self, context):
        images = ["$Vector", "$Ambient", "$Direct"]
        for image in images:
            if not pack_image(image):
                error = "Couldn't pack " + image + " image"
                self.report({"ERROR"}, error)
        return {'FINISHED'}


class TEST_OPERATOR(bpy.types.Operator):
    bl_idname = "q3.test_operator"
    bl_label = "TEST"
    bl_options = {"INTERNAL", "REGISTER"}

    def execute(self, context):

        addon_name = __name__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences

        # TODO: write shader dir to scene and read this
        import_settings = Import_Settings()
        import_settings.base_paths.append(prefs.base_path.replace("\\", "/"))

        if not import_settings.base_paths[0].endswith('/'):
            import_settings.base_paths[0] = import_settings.base_paths[0] + '/'

        import_settings = Import_Settings(
            base_paths=['G:/Xonotic/unpacked/'],
            preset=Preset.RENDERING.value,
        )

        VFS = Q3VFS()
        VFS.add_base('G:/Xonotic/unpacked/')
        VFS.build_index()

        file = ('G:/Xonotic/unpacked/'
                'maps/solarium.map')

        byte_array = VFS.get(file)
        entities = MAP.read_map_file(byte_array)
        objects = []

        for ent_id, ent in enumerate(entities):
            index_mapping = None
            current_index = 0
            positions = []
            uv_list = []
            indices = []
            materials = []
            material_ids = []
            material_sizes = {}
            if "surfaces" not in ent:
                continue
            for surf in ent["surfaces"]:
                if surf.type == "BRUSH":
                    for plane in surf.planes:
                        mat = plane.material
                        if mat not in materials:
                            materials.append(mat)

            material_sizes = (
                QuakeShader.get_shader_image_sizes(
                    VFS,
                    import_settings,
                    materials))

            for surf in ent["surfaces"]:
                if surf.type == "BRUSH":
                    final_points, uvs, faces, mats = parse_brush(
                        surf.planes, material_sizes)
                    for mat in mats:
                        if mat not in materials:
                            materials.append(mat)

                    index_mapping = [-2] * len(final_points)
                    for index, (point, uv) in enumerate(
                            zip(final_points, uvs)):
                        index_mapping[index] = current_index
                        current_index += 1
                        positions.append(point)
                        uv_list.append(uv)

                    for face, mat in zip(faces, mats):
                        # add vertices to model
                        model_indices = []
                        for index in face:
                            model_indices.append(index_mapping[index])
                        indices.append(model_indices)
                        material_ids.append(materials.index(mat))
            name = "entity" + str(ent_id)
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(
                positions,
                [],
                indices)

            for texture_instance in materials:
                mat = bpy.data.materials.get(texture_instance)
                if (mat is None):
                    mat = bpy.data.materials.new(name=texture_instance)
                mesh.materials.append(mat)
            mesh.polygons.foreach_set("material_index", material_ids)

            uvs = []
            uv_layer = "UVMap"
            for uv in uv_list:
                uvs.append(uv[0])
                uvs.append(1.0 - uv[1])

            mesh.uv_layers.new(do_init=False, name=uv_layer)
            mesh.uv_layers[uv_layer].data.foreach_set(
                "uv", uvs)

            mesh.use_auto_smooth = True
            mesh.update()
            mesh.validate()
            ob = bpy.data.objects.new(
                    name=name,
                    object_data=mesh)
            objects.append(ob)
            bpy.context.collection.objects.link(ob)

        QuakeShader.build_quake_shaders(VFS, import_settings, objects)
        return {'FINISHED'}


class Q3_PT_EntExportPanel(bpy.types.Panel):
    bl_name = "Q3_PT_ent_panel"
    bl_label = "Export"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Q3 Entities"

    @classmethod
    def poll(self, context):
        if "id_tech_3_importer_preset" in context.scene:
            return (context.object is not None and (
                context.scene.id_tech_3_importer_preset == "EDITING"))
        return False

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(
            text="Here you can export all the entities in "
            "the scene to different filetypes")
        op = layout.operator("q3.export_ent", text="Export .ent")
        # op = layout.operator("q3.export_map", text="Export .map")
        # is it any different to .ent?
        op = layout.operator("q3.patch_bsp_ents", text="Patch .bsp Entities")


class Q3_PT_DataExportPanel(bpy.types.Panel):
    bl_idname = "Q3_PT_data_export_panel"
    bl_label = "Patch BSP Data"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Q3 Data"

    def draw(self, context):
        layout = self.layout
        layout.label(text="1. Prepare your scene for baking")
        layout.separator()
        op = layout.operator("q3.prepare_lm_baking",
                             text="2. Prepare Lightmap Baking")
        layout.separator()
        layout.label(text='3. Keep the selection of objects and bake light:')
        layout.label(text='Bake Type: Diffuse only Direct and Indirect')
        layout.label(text='Margin: 1 px')
        layout.separator()
        op = layout.operator("q3.pack_lightmap_images",
                             text="4. Pack and Save Baked Images")
        layout.separator()
        layout.label(text='5. Denoise $lightmap_bake and $vertmap_bake (opt.)')
        layout.label(
            text='Make sure your Images you want to be baked are named')
        layout.label(text='$lightmap_bake and $vertmap_bake')
        layout.separator()
        op = layout.operator("q3.store_vertex_colors",
                             text="6. Preview Vertex Colors (opt.)")
        layout.separator()
        op = layout.operator("q3.create_lightgrid", text="7. Create Lightgrid")
        layout.separator()
        layout.label(text="8. Select the LightGrid object and bake light:")
        layout.label(text='Bake Type: Diffuse only Direct and Indirect')
        layout.label(text='Margin: 0 px!')
        layout.separator()
        op = layout.operator("q3.convert_baked_lightgrid",
                             text="9. Convert Baked Lightgrid")
        layout.separator()
        op = layout.operator("q3.pack_lightgrid_images",
                             text="10. Pack and Save Converted Images")
        layout.separator()
        op = layout.operator("q3.patch_bsp_data", text="11. Patch .bsp Data")

        layout.separator()
        op = layout.operator("q3.test_operator", text="TEST OPERATOR")


class Reload_preview_shader(bpy.types.Operator):
    """Reload Shaders"""
    bl_idname = "q3mapping.reload_preview_shader"
    bl_label = "Reload Eevee Shaders"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_name = __name__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences

        # TODO: write shader dir to scene and read this
        base_path = prefs.base_path.replace("\\", "/")
        if not base_path.endswith('/'):
            base_path = base_path + '/'

        import_settings = Import_Settings(
            base_paths=[base_path],
            preset=Preset.PREVIEW.value,
        )

        # initialize virtual file system
        VFS = Q3VFS()
        for base_path in import_settings.base_paths:
            VFS.add_base(base_path)
        VFS.build_index()

        objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        QuakeShader.build_quake_shaders(VFS, import_settings, objs)

        return {'FINISHED'}


class Reload_render_shader(bpy.types.Operator):
    """Reload Shaders"""
    bl_idname = "q3mapping.reload_render_shader"
    bl_label = "Reload Cycles Shaders"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_name = __name__.split('.')[0]
        prefs = context.preferences.addons[addon_name].preferences

        # TODO: write shader dir to scene and read this
        base_path = prefs.base_path.replace("\\", "/")
        if not base_path.endswith('/'):
            base_path = base_path + '/'

        import_settings = Import_Settings(
            base_paths=[base_path],
            preset=Preset.RENDERING.value,
        )

        # initialize virtual file system
        VFS = Q3VFS()
        for base_path in import_settings.base_paths:
            VFS.add_base(base_path)
        VFS.build_index()

        objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        QuakeShader.build_quake_shaders(VFS, import_settings, objs)

        return {'FINISHED'}
