bl_info = {
    "name": "ShotMaster",
    "author": "Zac Counts",
    "version": (1, 4),
    "blender": (4, 3, 2),
    "location": "View3D > Sidebar > ShotMaster",
    "description": "Advanced camera management for film production and previsualization",
    "category": "3D View",
}

import bpy
import os
import math
import mathutils
import time
import datetime
from bpy.props import (StringProperty, IntProperty, EnumProperty, 
                       PointerProperty, CollectionProperty, BoolProperty,
                       FloatProperty, FloatVectorProperty)
from bpy.types import (Panel, Operator, PropertyGroup, 
                      UIList, AddonPreferences, Menu)

# --------------------------------
# Constants and Helpers
# --------------------------------

# Sensor size presets with actual dimensions in mm [width, height]
SENSOR_SIZES = [
    ('FULL_FRAME', "Full Frame", "35mm Full Frame (36×24mm)", 36.0, 24.0),
    ('APS_C', "APS-C", "APS-C (23.6×15.7mm)", 23.6, 15.7),
    ('MICRO_FOUR_THIRDS', "Micro Four Thirds", "Micro Four Thirds (17.3×13mm)", 17.3, 13.0),
    ('ONE_INCH', "1-inch", "1-inch (13.2×8.8mm)", 13.2, 8.8),
    ('ALEXA_LF', "Arri Alexa LF", "Arri Alexa LF (36.70×25.54mm)", 36.70, 25.54),
    ('ALEXA_MINI', "Arri Alexa Mini", "Arri Alexa Mini (28.25×18.17mm)", 28.25, 18.17),
    ('RED_MONSTRO', "RED Monstro", "RED Monstro (40.96×21.60mm)", 40.96, 21.60),
    ('RED_HELIUM', "RED Helium", "RED Helium (29.90×15.77mm)", 29.90, 15.77),
    ('BLACKMAGIC_URSA', "Blackmagic URSA", "Blackmagic URSA (25.34×14.25mm)", 25.34, 14.25),
    ('SONY_VENICE', "Sony Venice", "Sony Venice (36×24mm)", 36.0, 24.0),
    ('CUSTOM', "Custom", "Custom sensor size", 0.0, 0.0), # Will use camera's current values
]

# Shot size presets
SHOT_SIZES = [
    ('EXTREME_WIDE', "Extreme Wide Shot", "Establishing shot showing a large area"),
    ('WIDE', "Wide Shot", "Shows the subject and their surroundings"),
    ('FULL', "Full Shot", "Shows the full body of the subject"),
    ('MID', "Mid Shot", "Shows subject from the waist up"),
    ('MEDIUM_CLOSE', "Medium Close-Up", "Shows subject from chest up"),
    ('CLOSE', "Close-Up", "Shows subject's face"),
    ('EXTREME_CLOSE', "Extreme Close-Up", "Shows a detail, like eyes"),
    ('OTHER', "Other", "Custom shot size"),
]

# Shot type presets
SHOT_TYPES = [
    ('STATIC', "Static", "Camera doesn't move"),
    ('PAN', "Pan", "Camera rotates horizontally"),
    ('TILT', "Tilt", "Camera rotates vertically"),
    ('DOLLY', "Dolly", "Camera moves forward/backward"),
    ('TRUCK', "Truck", "Camera moves left/right"),
    ('PEDESTAL', "Pedestal", "Camera moves up/down"),
    ('ZOOM', "Zoom", "Lens zooms in/out"),
    ('HAND_HELD', "Hand Held", "Hand-held or deliberately unstable camera"),
    ('CRANE', "Crane", "Camera on a crane or jib"),
    ('STEADICAM', "Steadicam", "Smooth moving camera"),
    ('AERIAL', "Aerial", "Shot from above, drone etc."),
    ('OTHER', "Other", "Custom shot type"),
]

# Equipment presets
EQUIPMENT_TYPES = [
    ('TRIPOD', "Tripod", "Standard tripod"),
    ('SHOULDER', "Shoulder Rig", "Shoulder-mounted camera"),
    ('GIMBAL', "Gimbal", "Motorized gimbal stabilizer"),
    ('DOLLY_TRACK', "Dolly/Track", "Camera dolly on tracks"),
    ('SLIDER', "Slider", "Camera slider"),
    ('CRANE', "Crane/Jib", "Camera crane or jib"),
    ('STEADICAM', "Steadicam", "Steadicam stabilizer"),
    ('DRONE', "Drone", "Aerial drone"),
    ('HANDHELD', "Handheld", "Handheld without rig"),
    ('VIRTUAL', "Virtual", "Computer controlled/virtual"),
    ('OTHER', "Other", "Custom equipment"),
]

# Pass types for rendering
PASS_TYPES = [
    ('BEAUTY', "Beauty", "Main beauty render"),
    ('DIFFUSE', "Diffuse", "Diffuse pass"),
    ('SPECULAR', "Specular", "Specular pass"),
    ('SHADOW', "Shadow", "Shadow pass"),
    ('AO', "Ambient Occlusion", "AO pass"),
    ('DEPTH', "Depth", "Depth pass"),
    ('NORMAL', "Normal", "Normal pass"),
    ('MIST', "Mist", "Mist/fog/depth pass"),
    ('EMISSION', "Emission", "Emission pass"),
    ('ENVIRONMENT', "Environment", "Environment contribution pass"),
    ('CUSTOM', "Custom", "Custom pass"),
]

# White balance presets (in Kelvin)
WHITE_BALANCE_PRESETS = [
    ('CUSTOM', "Custom", "Custom white balance", 6500),
    ('DAYLIGHT', "Daylight", "Daylight (5500K)", 5500),
    ('CLOUDY', "Cloudy", "Cloudy daylight (6500K)", 6500),
    ('SHADE', "Shade", "Shade (7500K)", 7500),
    ('TUNGSTEN', "Tungsten", "Tungsten light (3200K)", 3200),
    ('FLUORESCENT', "Fluorescent", "Fluorescent light (4000K)", 4000),
    ('INCANDESCENT', "Incandescent", "Incandescent light (2700K)", 2700),
    ('FLASH', "Flash", "Camera flash (5500K)", 5500),
    ('SUNSET', "Sunset", "Sunset/sunrise (3500K)", 3500),
    ('CANDLELIGHT', "Candlelight", "Candlelight (1900K)", 1900),
]

# Convert to format needed for EnumProperty
SENSOR_SIZES_ENUM = [(item[0], item[1], item[2]) for item in SENSOR_SIZES]
WHITE_BALANCE_ENUM = [(item[0], item[1], item[2]) for item in WHITE_BALANCE_PRESETS]

# Helper function to get sensor name from ID
def get_sensor_name(sensor_id):
    for sensor in SENSOR_SIZES:
        if sensor[0] == sensor_id:
            return sensor[1]
    return "Unknown"

# Helper function to get sensor dimensions from ID
def get_sensor_dimensions(sensor_id):
    for sensor in SENSOR_SIZES:
        if sensor[0] == sensor_id:
            return (sensor[3], sensor[4])
    return (36.0, 24.0)  # Default to full frame

# Helper function to get white balance temperature from ID
def get_white_balance_temp(wb_id):
    for wb in WHITE_BALANCE_PRESETS:
        if wb[0] == wb_id:
            return wb[3]
    return 6500  # Default to daylight

# Get all view layers in the scene
def get_view_layers():
    return [(layer.name, layer.name, f"View Layer: {layer.name}") for layer in bpy.context.scene.view_layers]

# Get all collections in the scene
def get_collections():
    collections = []
    
    def traverse_collection(collection, level=0):
        collections.append((collection.name, collection.name, f"Collection: {collection.name}"))
        for child in collection.children:
            traverse_collection(child, level + 1)
    
    # Start with the master collection
    traverse_collection(bpy.context.scene.collection)
    return collections

# --------------------------------
# Property Update Functions
# --------------------------------

# Function to update camera sensor size when preset changes
def update_sensor_size(self, context):
    # Get the camera this property belongs to
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA' and hasattr(obj, 'shotmaster_camera'):
            if obj.shotmaster_camera == self:
                camera = obj
                if camera.type == 'CAMERA':
                    # Get dimensions for the selected preset
                    width, height = get_sensor_dimensions(self.sensor_size)
                    
                    # Skip update for custom preset
                    if self.sensor_size == 'CUSTOM':
                        return
                    
                    # Update camera sensor size
                    camera.data.sensor_width = width
                    camera.data.sensor_height = height
                    
                    # Ensure sensor fit is set to AUTO
                    camera.data.sensor_fit = 'AUTO'
                    return  # Only update the camera this property belongs to

# Function to update white balance when preset changes
def update_white_balance_preset(self, context):
    if self.white_balance_preset != 'CUSTOM':
        temp = get_white_balance_temp(self.white_balance_preset)
        self.white_balance_temp = temp

# Function to update camera color display
def update_camera_color(self, context):
    # This function exists to trigger UI redraw
    pass

# Function to update group color display
def update_group_color(self, context):
    # This function exists to trigger UI redraw
    pass

# --------------------------------
# Render Pass Property Group
# --------------------------------

class RenderPass(PropertyGroup):
    enabled: BoolProperty(
        name="Enable",
        description="Enable this render pass",
        default=True
    )
    
    pass_type: EnumProperty(
        name="Pass Type",
        description="Type of render pass",
        items=PASS_TYPES,
        default='BEAUTY'
    )
    
    name: StringProperty(
        name="Pass Name",
        description="Name for this render pass (used in filename)",
        default="beauty"
    )

# --------------------------------
# Camera Property Groups
# --------------------------------

# Camera Group property group
class CameraGroup(PropertyGroup):
    # Basic properties
    name: StringProperty(
        name="Group Name",
        description="Name of the camera group",
        default="Camera Group"
    )
    
    # UI display properties
    is_expanded: BoolProperty(
        name="Expanded",
        description="Show cameras in this group",
        default=True
    )
    
    # Visual properties
    color: FloatVectorProperty(
        name="Group Color",
        description="Color for this camera group (for UI display only)",
        subtype='COLOR',
        default=(0.91, 0.33, 0.13, 1.0),  # Blender orange
        min=0.0, max=1.0,
        size=4,
        update=update_group_color
    )
    
    # Note properties
    notes: StringProperty(
        name="Group Notes",
        description="Notes about this camera group",
        default=""
    )
    
    # Group output settings
    use_custom_output_path: BoolProperty(
        name="Custom Output Path",
        description="Use a custom output path for all cameras in this group",
        default=False
    )
    
    output_path: StringProperty(
        name="Group Output Path",
        description="Output path for all cameras in this group",
        default="",
        subtype='DIR_PATH'
    )
    
    # Group render settings overrides
    use_custom_render_settings: BoolProperty(
        name="Custom Render Settings",
        description="Use custom render settings for all cameras in this group",
        default=False
    )
    
    render_engine: EnumProperty(
        name="Render Engine",
        description="Render engine to use",
        items=[
            ('CYCLES', "Cycles", "Cycles raytracing engine"),
            ('BLENDER_EEVEE', "Eevee", "Eevee rasterization engine"),
            ('BLENDER_WORKBENCH', "Workbench", "Workbench engine"),
        ],
        default='CYCLES'
    )
    
    cycles_samples: IntProperty(
        name="Cycles Samples",
        description="Number of Cycles samples to render",
        min=1,
        default=128
    )
    
    eevee_samples: IntProperty(
        name="Eevee Samples",
        description="Number of Eevee samples to render",
        min=1,
        default=64
    )
    
    use_custom_resolution: BoolProperty(
        name="Custom Resolution",
        description="Use custom resolution for this group",
        default=False
    )
    
    resolution_x: IntProperty(
        name="Width",
        description="Output width in pixels",
        default=1920,
        min=1
    )
    
    resolution_y: IntProperty(
        name="Height",
        description="Output height in pixels",
        default=1080,
        min=1
    )
    
    resolution_percentage: IntProperty(
        name="Resolution %",
        description="Percentage of resolution to render",
        default=100,
        min=1, max=100
    )
    
    # View layer management
    use_custom_view_layer: BoolProperty(
        name="Custom View Layer",
        description="Use a specific view layer for this group",
        default=False
    )
    
    view_layer: StringProperty(
        name="View Layer",
        description="View layer to use for rendering"
    )
    
    # Collections visibility
    use_custom_collections: BoolProperty(
        name="Custom Collections",
        description="Use custom collection visibility for this group",
        default=False
    )
    
    # We'll handle collections visibility through functions rather than properties
    # as it's a dynamic list

# Custom properties for cameras
class ShotMasterCamera(PropertyGroup):
    # Basic properties
    use_custom_render_settings: BoolProperty(
        name="Custom Render Settings",
        description="Use custom render settings for this camera",
        default=False
    )
    
    # Resolution settings
    use_custom_resolution: BoolProperty(
        name="Custom Resolution",
        description="Use custom resolution for this camera",
        default=False
    )
    
    resolution_x: IntProperty(
        name="Width",
        description="Output width in pixels",
        default=1920,
        min=1
    )
    
    resolution_y: IntProperty(
        name="Height",
        description="Output height in pixels",
        default=1080,
        min=1
    )
    
    resolution_percentage: IntProperty(
        name="Resolution %",
        description="Percentage of resolution to render",
        default=100,
        min=1, max=100
    )
    
    # Engine settings
    render_engine: EnumProperty(
        name="Render Engine",
        description="Render engine to use",
        items=[
            ('CYCLES', "Cycles", "Cycles raytracing engine"),
            ('BLENDER_EEVEE', "Eevee", "Eevee rasterization engine"),
            ('BLENDER_WORKBENCH', "Workbench", "Workbench engine"),
        ],
        default='CYCLES'
    )
    
    cycles_samples: IntProperty(
        name="Cycles Samples",
        description="Number of Cycles samples to render",
        min=1,
        default=128
    )
    
    eevee_samples: IntProperty(
        name="Eevee Samples",
        description="Number of Eevee samples to render",
        min=1,
        default=64
    )
    
    # Passes
    use_render_passes: BoolProperty(
        name="Use Render Passes",
        description="Render multiple passes (beauty, diffuse, etc.)",
        default=False
    )
    
    render_passes: CollectionProperty(
        name="Render Passes",
        description="List of render passes to output",
        type=RenderPass
    )
    
    active_pass_index: IntProperty(
        name="Active Pass Index",
        description="Index of the active render pass",
        default=0
    )
    
    # Output path settings
    use_custom_output_path: BoolProperty(
        name="Custom Output Path",
        description="Override group/master output path for this camera",
        default=False
    )
    
    output_path: StringProperty(
        name="Output Path",
        description="Directory to save renders",
        default="",
        subtype='DIR_PATH'
    )
    
    # File format settings
    file_format: EnumProperty(
        name="Format",
        description="Output file format",
        items=(
            ('PNG', "PNG", "PNG format"),
            ('JPEG', "JPEG", "JPEG format"),
            ('OPEN_EXR', "OpenEXR", "OpenEXR format"),
            ('TIFF', "TIFF", "TIFF format"),
        ),
        default='PNG'
    )
    
    # Filename pattern
    filename: StringProperty(
        name="Filename",
        description="Base filename for render output",
        default="shot"
    )
    
    # View layer management
    use_custom_view_layer: BoolProperty(
        name="Custom View Layer",
        description="Use a specific view layer for this camera",
        default=False
    )
    
    view_layer: StringProperty(
        name="View Layer",
        description="View layer to use for rendering"
    )
    
    # Collections visibility
    use_custom_collections: BoolProperty(
        name="Custom Collections",
        description="Use custom collection visibility for this camera",
        default=False
    )
    
    # We'll handle collections visibility through functions rather than properties
    # as it's a dynamic list
    
    # Lens and sensor properties
    sensor_size: EnumProperty(
        name="Sensor Size",
        description="Camera sensor size preset",
        items=SENSOR_SIZES_ENUM,
        default='FULL_FRAME',
        update=update_sensor_size
    )
    
    # White balance
    white_balance_preset: EnumProperty(
        name="White Balance",
        description="White balance preset",
        items=WHITE_BALANCE_ENUM,
        default='DAYLIGHT',
        update=update_white_balance_preset
    )
    
    white_balance_temp: IntProperty(
        name="Color Temperature",
        description="White balance color temperature in Kelvin",
        default=5500,
        min=1000, max=40000
    )
    
    # Added this to store focus target object
    focus_target: PointerProperty(
        name="Focus Target",
        description="Object to focus on",
        type=bpy.types.Object
    )
    
    # UI display state
    is_expanded: BoolProperty(
        name="Expanded",
        description="Show expanded camera settings",
        default=True
    )
    
    # Property panel visibility state and active tab
    show_properties: BoolProperty(
        name="Show Properties",
        description="Show camera properties panel",
        default=False
    )
    
    active_property_tab: EnumProperty(
        name="Active Property Tab",
        description="Active tab in the properties panel",
        items=[
            ('CAMERA', "Camera", "Camera settings"),
            ('RENDER', "Render", "Render settings"),
            ('OUTPUT', "Output", "Output settings"),
            ('NOTES', "Notes", "Camera notes"),
            ('LAYERS', "Layers", "View layers and collections"),
        ],
        default='CAMERA'
    )
    
    # Visual properties
    color: FloatVectorProperty(
        name="Camera Color",
        description="Color for this camera (for UI display only)",
        subtype='COLOR',
        default=(0.91, 0.33, 0.13, 1.0),  # Blender orange
        min=0.0, max=1.0,
        size=4,
        update=update_camera_color
    )
    
    # Camera group reference
    group: StringProperty(
        name="Group",
        description="Camera group this camera belongs to",
        default=""
    )
    
    # Animation settings
    use_custom_frames: BoolProperty(
        name="Custom Frame Range",
        description="Use custom frame range for this camera instead of master",
        default=False
    )
    
    start_frame: IntProperty(
        name="Start Frame",
        description="Start frame for animation rendering",
        default=1,
        min=0
    )
    
    end_frame: IntProperty(
        name="End Frame",
        description="End frame for animation rendering",
        default=250,
        min=0
    )
    
    # Shot information (notes)
    notes: StringProperty(
        name="Shot Notes",
        description="General notes about this shot",
        default=""
    )
    
    shot_size: EnumProperty(
        name="Shot Size",
        description="Size/framing of the shot",
        items=SHOT_SIZES,
        default='WIDE'
    )
    
    shot_type: EnumProperty(
        name="Shot Type",
        description="Type of camera movement",
        items=SHOT_TYPES,
        default='STATIC'
    )
    
    shot_movement: StringProperty(
        name="Shot Movement",
        description="Details about camera movement",
        default=""
    )
    
    equipment: EnumProperty(
        name="Equipment",
        description="Camera support/equipment",
        items=EQUIPMENT_TYPES,
        default='TRIPOD'
    )
    
    equipment_notes: StringProperty(
        name="Equipment Notes",
        description="Additional equipment notes",
        default=""
    )

# Scene properties for master animation and render settings
class ShotMasterSettings(PropertyGroup):
    # Frame range
    master_start_frame: IntProperty(
        name="Master Start Frame",
        description="Default start frame for all cameras",
        default=1,
        min=0
    )
    
    master_end_frame: IntProperty(
        name="Master End Frame",
        description="Default end frame for all cameras",
        default=250,
        min=0
    )
    
    # Output path
    master_output_path: StringProperty(
        name="Master Output Path",
        description="Default output directory for all renders",
        default="//renders/",
        subtype='DIR_PATH'
    )
    
    # Render settings
    master_resolution_x: IntProperty(
        name="Width",
        description="Default output width in pixels",
        default=1920,
        min=1
    )
    
    master_resolution_y: IntProperty(
        name="Height",
        description="Default output height in pixels",
        default=1080,
        min=1
    )
    
    master_resolution_percentage: IntProperty(
        name="Resolution %",
        description="Default percentage of resolution to render",
        default=100,
        min=1, max=100
    )
    
    master_render_engine: EnumProperty(
        name="Render Engine",
        description="Default render engine to use",
        items=[
            ('CYCLES', "Cycles", "Cycles raytracing engine"),
            ('BLENDER_EEVEE', "Eevee", "Eevee rasterization engine"),
            ('BLENDER_WORKBENCH', "Workbench", "Workbench engine"),
        ],
        default='CYCLES'
    )
    
    master_cycles_samples: IntProperty(
        name="Cycles Samples",
        description="Default number of Cycles samples to render",
        min=1,
        default=128
    )
    
    master_eevee_samples: IntProperty(
        name="Eevee Samples",
        description="Default number of Eevee samples to render",
        min=1,
        default=64
    )
    
    # Statistics tracking
    total_renders: IntProperty(
        name="Total Renders",
        description="Total number of renders performed",
        default=0,
        min=0
    )
    
    last_render_time: FloatProperty(
        name="Last Render Time",
        description="Time taken for the last render (seconds)",
        default=0.0,
        min=0.0
    )
    
    total_render_time: FloatProperty(
        name="Total Render Time",
        description="Total time spent rendering (seconds)",
        default=0.0,
        min=0.0
    )
    
    # Settings
    show_advanced_options: BoolProperty(
        name="Show Advanced Options",
        description="Show advanced options in the UI",
        default=False
    )

# --------------------------------
# ShotMaster Manager Class
# --------------------------------

class ShotMasterManager:
    @staticmethod
    def get_all_cameras():
        """Return all camera objects in the scene"""
        return [obj for obj in bpy.context.scene.objects if obj.type == 'CAMERA']
    
    @staticmethod
    def get_cameras_in_group(group_name):
        """Return all cameras in the specified group"""
        if not group_name:
            return []
        return [cam for cam in ShotMasterManager.get_all_cameras() if cam.shotmaster_camera.group == group_name]
    
    @staticmethod
    def get_ungrouped_cameras():
        """Return all cameras not in any group"""
        return [cam for cam in ShotMasterManager.get_all_cameras() if not cam.shotmaster_camera.group]
    
    @staticmethod
    def create_camera(name="Shot", location=(0, 0, 0), rotation=(0, 0, 0), group=""):
        """Create a new camera with shotmaster properties"""
        # Create camera data and object
        cam_data = bpy.data.cameras.new(name)
        cam_obj = bpy.data.objects.new(name, cam_data)
        
        # Set passepartout to 1 by default
        cam_data.passepartout_alpha = 1.0
        
        # Link to scene
        try:
            bpy.context.collection.objects.link(cam_obj)
        except RuntimeError:
            # Fallback to scene collection if active collection is hidden
            bpy.context.scene.collection.objects.link(cam_obj)
        
        # Set location and rotation
        cam_obj.location = location
        cam_obj.rotation_euler = rotation
        
        # Initialize shotmaster properties if not already present
        if not cam_obj.shotmaster_camera:
            # This will use default values from the PropertyGroup
            pass
        
        # Assign to group if specified
        if group:
            cam_obj.shotmaster_camera.group = group
        
        # Apply default sensor size
        width, height = get_sensor_dimensions(cam_obj.shotmaster_camera.sensor_size)
        cam_data.sensor_width = width
        cam_data.sensor_height = height
        
        # Initialize with one default beauty pass
        if len(cam_obj.shotmaster_camera.render_passes) == 0:
            new_pass = cam_obj.shotmaster_camera.render_passes.add()
            new_pass.name = "beauty"
            new_pass.pass_type = 'BEAUTY'
            new_pass.enabled = True
            
        return cam_obj
    
    @staticmethod
    def duplicate_camera(camera):
        """Duplicate an existing camera with its properties"""
        if not camera or camera.type != 'CAMERA':
            return None
            
        # Get original camera name and create new name
        original_name = camera.name
        new_name = f"{original_name}_copy"
        
        # Create new camera data and object
        new_cam_data = camera.data.copy()
        new_cam_obj = bpy.data.objects.new(new_name, new_cam_data)
        
        # Copy transform
        new_cam_obj.location = camera.location.copy()
        new_cam_obj.rotation_euler = camera.rotation_euler.copy()
        new_cam_obj.scale = camera.scale.copy()
        
        # Link to scene
        try:
            bpy.context.collection.objects.link(new_cam_obj)
        except RuntimeError:
            # Fallback to scene collection if active collection is hidden
            bpy.context.scene.collection.objects.link(new_cam_obj)
        
        # Copy shotmaster camera properties
        if hasattr(camera, 'shotmaster_camera'):
            # Basic properties
            new_cam_obj.shotmaster_camera.resolution_x = camera.shotmaster_camera.resolution_x
            new_cam_obj.shotmaster_camera.resolution_y = camera.shotmaster_camera.resolution_y
            new_cam_obj.shotmaster_camera.resolution_percentage = camera.shotmaster_camera.resolution_percentage
            new_cam_obj.shotmaster_camera.use_custom_resolution = camera.shotmaster_camera.use_custom_resolution
            
            # Render settings
            new_cam_obj.shotmaster_camera.render_engine = camera.shotmaster_camera.render_engine
            new_cam_obj.shotmaster_camera.cycles_samples = camera.shotmaster_camera.cycles_samples
            new_cam_obj.shotmaster_camera.eevee_samples = camera.shotmaster_camera.eevee_samples
            new_cam_obj.shotmaster_camera.use_custom_render_settings = camera.shotmaster_camera.use_custom_render_settings
            
            # Output settings
            new_cam_obj.shotmaster_camera.use_custom_output_path = camera.shotmaster_camera.use_custom_output_path
            new_cam_obj.shotmaster_camera.output_path = camera.shotmaster_camera.output_path
            new_cam_obj.shotmaster_camera.file_format = camera.shotmaster_camera.file_format
            new_cam_obj.shotmaster_camera.filename = camera.shotmaster_camera.filename
            
            # Camera settings
            new_cam_obj.shotmaster_camera.sensor_size = camera.shotmaster_camera.sensor_size
            new_cam_obj.shotmaster_camera.white_balance_preset = camera.shotmaster_camera.white_balance_preset
            new_cam_obj.shotmaster_camera.white_balance_temp = camera.shotmaster_camera.white_balance_temp
            
            # Group and color
            new_cam_obj.shotmaster_camera.group = camera.shotmaster_camera.group
            new_cam_obj.shotmaster_camera.color = camera.shotmaster_camera.color
            
            # Animation
            new_cam_obj.shotmaster_camera.use_custom_frames = camera.shotmaster_camera.use_custom_frames
            new_cam_obj.shotmaster_camera.start_frame = camera.shotmaster_camera.start_frame
            new_cam_obj.shotmaster_camera.end_frame = camera.shotmaster_camera.end_frame
            
            # Notes
            new_cam_obj.shotmaster_camera.notes = camera.shotmaster_camera.notes
            new_cam_obj.shotmaster_camera.shot_size = camera.shotmaster_camera.shot_size
            new_cam_obj.shotmaster_camera.shot_type = camera.shotmaster_camera.shot_type
            new_cam_obj.shotmaster_camera.shot_movement = camera.shotmaster_camera.shot_movement
            new_cam_obj.shotmaster_camera.equipment = camera.shotmaster_camera.equipment
            new_cam_obj.shotmaster_camera.equipment_notes = camera.shotmaster_camera.equipment_notes
            
            # View layers and collections
            new_cam_obj.shotmaster_camera.use_custom_view_layer = camera.shotmaster_camera.use_custom_view_layer
            new_cam_obj.shotmaster_camera.view_layer = camera.shotmaster_camera.view_layer
            new_cam_obj.shotmaster_camera.use_custom_collections = camera.shotmaster_camera.use_custom_collections
            
            # Copy focus target if exists
            if camera.shotmaster_camera.focus_target:
                new_cam_obj.shotmaster_camera.focus_target = camera.shotmaster_camera.focus_target
            
            # Copy render passes
            new_cam_obj.shotmaster_camera.use_render_passes = camera.shotmaster_camera.use_render_passes
            
            # Clear existing passes (default one)
            while len(new_cam_obj.shotmaster_camera.render_passes) > 0:
                new_cam_obj.shotmaster_camera.render_passes.remove(0)
                
            # Copy passes from original camera
            for pass_item in camera.shotmaster_camera.render_passes:
                new_pass = new_cam_obj.shotmaster_camera.render_passes.add()
                new_pass.name = pass_item.name
                new_pass.pass_type = pass_item.pass_type
                new_pass.enabled = pass_item.enabled
        
        return new_cam_obj
    
    @staticmethod
    def set_active_camera(camera):
        """Set the specified camera as the active scene camera"""
        if camera and camera.type == 'CAMERA':
            bpy.context.scene.camera = camera
            return True
        return False
    
    @staticmethod
    def get_camera_output_path(camera, render_animation=False, pass_name=None):
        """Determine the output path based on hierarchy: camera > group > master"""
        context = bpy.context
        
        # Start with master path
        base_path = bpy.path.abspath(context.scene.shotmaster_settings.master_output_path)
        
        # Get camera group
        group_name = camera.shotmaster_camera.group
        
        # If camera has a group, check if group has custom path
        if group_name:
            for group in context.scene.shotmaster_camera_groups:
                if group.name == group_name and group.use_custom_output_path:
                    if group.output_path:
                        base_path = bpy.path.abspath(group.output_path)
                    break
        
        # Check if camera has custom path
        if camera.shotmaster_camera.use_custom_output_path and camera.shotmaster_camera.output_path:
            base_path = bpy.path.abspath(camera.shotmaster_camera.output_path)
        
        # Create folder structure
        if group_name:
            # Add group folder
            sanitized_group_name = "".join(c for c in group_name if c.isalnum() or c in " _-").strip()
            sanitized_group_name = sanitized_group_name.replace(" ", "_")
            group_path = os.path.join(base_path, sanitized_group_name)
        else:
            # Use 'ungrouped' for cameras without a group
            group_path = os.path.join(base_path, "ungrouped")
        
        # Create camera-specific folder 
        sanitized_camera_name = "".join(c for c in camera.name if c.isalnum() or c in " _-").strip()
        sanitized_camera_name = sanitized_camera_name.replace(" ", "_")
        
        # For animations, create a separate folder hierarchy
        if render_animation:
            if pass_name:
                # Add pass subfolder for animations with passes
                final_path = os.path.join(group_path, sanitized_camera_name, "animation", pass_name)
            else:
                # Regular animation folder
                final_path = os.path.join(group_path, sanitized_camera_name, "animation")
        else:
            # For stills with passes
            if pass_name:
                final_path = os.path.join(group_path, sanitized_camera_name, "stills", pass_name)
            else:
                # Regular stills, just use camera folder
                final_path = os.path.join(group_path, sanitized_camera_name, "stills")
        
        return final_path
    
    @staticmethod
    def setup_render_settings(camera, is_viewport=False):
        """Apply render settings based on hierarchy: camera > group > master"""
        context = bpy.context
        render = context.scene.render
        
        # Store original settings for restoration
        original_settings = {
            'engine': context.scene.render.engine,
            'resolution_x': render.resolution_x,
            'resolution_y': render.resolution_y,
            'resolution_percentage': render.resolution_percentage,
            'filepath': render.filepath,
            'file_format': render.image_settings.file_format,
            'active_camera': context.scene.camera,
            'frame_start': context.scene.frame_start,
            'frame_end': context.scene.frame_end
        }
        
        # Start with master settings
        render.engine = context.scene.shotmaster_settings.master_render_engine
        render.resolution_x = context.scene.shotmaster_settings.master_resolution_x
        render.resolution_y = context.scene.shotmaster_settings.master_resolution_y
        render.resolution_percentage = context.scene.shotmaster_settings.master_resolution_percentage
        
        if render.engine == 'CYCLES':
            context.scene.cycles.samples = context.scene.shotmaster_settings.master_cycles_samples
        elif render.engine == 'BLENDER_EEVEE':
            context.scene.eevee.taa_render_samples = context.scene.shotmaster_settings.master_eevee_samples
        
        # Apply group settings if applicable
        group_name = camera.shotmaster_camera.group
        if group_name:
            for group in context.scene.shotmaster_camera_groups:
                if group.name == group_name:
                    if group.use_custom_render_settings:
                        render.engine = group.render_engine
                        
                        if group.use_custom_resolution:
                            render.resolution_x = group.resolution_x
                            render.resolution_y = group.resolution_y
                            render.resolution_percentage = group.resolution_percentage
                            
                        if render.engine == 'CYCLES':
                            context.scene.cycles.samples = group.cycles_samples
                        elif render.engine == 'BLENDER_EEVEE':
                            context.scene.eevee.taa_render_samples = group.eevee_samples
                    
                    # Apply custom view layer if specified
                    if group.use_custom_view_layer and group.view_layer in context.scene.view_layers:
                        context.window.view_layer = context.scene.view_layers[group.view_layer]
                    
                    # TODO: Apply custom collections visibility
                    break
        
        # Finally apply camera-specific settings
        if camera.shotmaster_camera.use_custom_render_settings:
            render.engine = camera.shotmaster_camera.render_engine
            
            if camera.shotmaster_camera.use_custom_resolution:
                render.resolution_x = camera.shotmaster_camera.resolution_x
                render.resolution_y = camera.shotmaster_camera.resolution_y
                render.resolution_percentage = camera.shotmaster_camera.resolution_percentage
                
            if render.engine == 'CYCLES':
                context.scene.cycles.samples = camera.shotmaster_camera.cycles_samples
            elif render.engine == 'BLENDER_EEVEE':
                context.scene.eevee.taa_render_samples = camera.shotmaster_camera.eevee_samples
        
        # Apply custom view layer if specified for camera
        if camera.shotmaster_camera.use_custom_view_layer and camera.shotmaster_camera.view_layer in context.scene.view_layers:
            context.window.view_layer = context.scene.view_layers[camera.shotmaster_camera.view_layer]
        
        # TODO: Apply custom collections visibility for camera
        
        # Apply white balance - this would require a temporary color management setup
        # or post-processing, as Blender doesn't have direct white balance control
        
        # Set frame range based on camera settings or master settings
        if camera.shotmaster_camera.use_custom_frames:
            context.scene.frame_start = camera.shotmaster_camera.start_frame
            context.scene.frame_end = camera.shotmaster_camera.end_frame
        else:
            context.scene.frame_start = context.scene.shotmaster_settings.master_start_frame
            context.scene.frame_end = context.scene.shotmaster_settings.master_end_frame
        
        # Set active camera
        context.scene.camera = camera
        
        if is_viewport:
            # For viewport renders, we don't need to set output path
            pass
        else:
            # Determine output format 
            render.image_settings.file_format = camera.shotmaster_camera.file_format
        
        return original_settings
    
    @staticmethod
    def restore_render_settings(original_settings):
        """Restore original render settings after rendering"""
        context = bpy.context
        render = context.scene.render
        
        render.engine = original_settings['engine']
        render.resolution_x = original_settings['resolution_x']
        render.resolution_y = original_settings['resolution_y']
        render.resolution_percentage = original_settings['resolution_percentage']
        render.filepath = original_settings['filepath']
        render.image_settings.file_format = original_settings['file_format']
        context.scene.camera = original_settings['active_camera']
        context.scene.frame_start = original_settings['frame_start']
        context.scene.frame_end = original_settings['frame_end']
    
    @staticmethod
    def render_from_camera(camera, render_animation=False, is_viewport=False):
        """Render from the specified camera using its settings"""
        if not camera or camera.type != 'CAMERA':
            return False
        
        context = bpy.context
        
        # Start timing the render
        start_time = time.time()
        success = False
        
        try:
            # Setup render settings
            original_settings = ShotMasterManager.setup_render_settings(camera, is_viewport)
            
            # If it's a viewport render, we just need to render to viewport
            if is_viewport:
                if render_animation:
                    # Currently viewport animation capture is not directly supported
                    # We could potentially use a screen capture technique or other methods
                    # For now, just use normal animation render
                    pass
                else:
                    # Viewport render
                    bpy.ops.render.opengl()
                    success = True
            else:
                # Get passes to render
                passes_to_render = []
                
                if camera.shotmaster_camera.use_render_passes:
                    # Add all enabled passes
                    for pass_item in camera.shotmaster_camera.render_passes:
                        if pass_item.enabled:
                            passes_to_render.append(pass_item.name)
                else:
                    # Just add a single 'None' to do a normal render
                    passes_to_render.append(None)
                
                # Render each pass
                for pass_name in passes_to_render:
                    try:
                        # Get output path for this pass
                        output_dir = ShotMasterManager.get_camera_output_path(camera, render_animation, pass_name)
                        
                        # Ensure directory exists
                        try:
                            os.makedirs(output_dir, exist_ok=True)
                        except Exception as e:
                            print(f"Error creating directory {output_dir}: {e}")
                            # Fallback to default path if we can't create the directory
                            output_dir = bpy.path.abspath("//renders/")
                            os.makedirs(output_dir, exist_ok=True)
                            
                        # Set output path and format
                        pass_suffix = f"_{pass_name}" if pass_name else ""
                        filename = f"{camera.shotmaster_camera.filename}_{camera.name}{pass_suffix}"
                        context.scene.render.filepath = os.path.join(output_dir, filename)
                        
                        # Render
                        if render_animation:
                            bpy.ops.render.render(animation=True)
                        else:
                            bpy.ops.render.render(write_still=True)
                            
                        success = True
                        
                    except Exception as e:
                        print(f"Error rendering pass {pass_name} from camera {camera.name}: {e}")
                        # Continue with next pass
            
            # Update render statistics
            end_time = time.time()
            render_time = end_time - start_time
            
            context.scene.shotmaster_settings.total_renders += 1
            context.scene.shotmaster_settings.last_render_time = render_time
            context.scene.shotmaster_settings.total_render_time += render_time
            
            return success
                
        except Exception as e:
            print(f"Error rendering from camera {camera.name}: {e}")
            return False
            
        finally:
            # Always restore original settings
            try:
                ShotMasterManager.restore_render_settings(original_settings)
            except Exception as e:
                print(f"Error restoring render settings: {e}")
    
    @staticmethod
    def calculate_dof_distance(camera):
        """Calculate the depth of field distance based on focus object or distance"""
        if not camera or camera.type != 'CAMERA':
            return "N/A"
            
        # Get camera data
        cam_data = camera.data
        
        if not cam_data.dof.use_dof:
            return "DOF disabled"
            
        # If using focus object
        if camera.shotmaster_camera.focus_target:
            target = camera.shotmaster_camera.focus_target
            if target:
                # Calculate distance between camera and target
                distance = (target.location - camera.location).length
                return f"{distance:.2f}m"
                
        # If using focus distance directly
        return f"{cam_data.dof.focus_distance:.2f}m"
    
    @staticmethod
    def get_camera_statistics(context=None):
        """Generate statistics about all cameras in the scene"""
        if context is None:
            context = bpy.context
            
        stats = {
            'total_cameras': 0,
            'total_groups': 0,
            'cameras_by_group': {},
            'render_engines': {
                'CYCLES': 0,
                'BLENDER_EEVEE': 0,
                'BLENDER_WORKBENCH': 0
            },
            'shot_types': {},
            'shot_sizes': {},
            'equipment': {},
            'total_renders': context.scene.shotmaster_settings.total_renders,
            'total_render_time': context.scene.shotmaster_settings.total_render_time,
            'average_render_time': 0,
            'last_render_time': context.scene.shotmaster_settings.last_render_time,
            'total_frames': 0
        }
        
        all_cameras = ShotMasterManager.get_all_cameras()
        stats['total_cameras'] = len(all_cameras)
        
        # Get group statistics
        groups = context.scene.shotmaster_camera_groups
        stats['total_groups'] = len(groups)
        
        # Initialize cameras by group count
        for group in groups:
            stats['cameras_by_group'][group.name] = 0
            
        # Add "Ungrouped" to the groups
        stats['cameras_by_group']['Ungrouped'] = 0
        
        # Process each camera
        for camera in all_cameras:
            # Update engine count based on what this camera would use
            engine = camera.shotmaster_camera.render_engine if camera.shotmaster_camera.use_custom_render_settings else context.scene.shotmaster_settings.master_render_engine
            stats['render_engines'][engine] += 1
            
            # Update shot type count
            shot_type = camera.shotmaster_camera.shot_type
            if shot_type in stats['shot_types']:
                stats['shot_types'][shot_type] += 1
            else:
                stats['shot_types'][shot_type] = 1
                
            # Update shot size count
            shot_size = camera.shotmaster_camera.shot_size
            if shot_size in stats['shot_sizes']:
                stats['shot_sizes'][shot_size] += 1
            else:
                stats['shot_sizes'][shot_size] = 1
                
            # Update equipment count
            equipment = camera.shotmaster_camera.equipment
            if equipment in stats['equipment']:
                stats['equipment'][equipment] += 1
            else:
                stats['equipment'][equipment] = 1
                
            # Update group count
            group_name = camera.shotmaster_camera.group
            if group_name:
                if group_name in stats['cameras_by_group']:
                    stats['cameras_by_group'][group_name] += 1
                else:
                    stats['cameras_by_group'][group_name] = 1
            else:
                stats['cameras_by_group']['Ungrouped'] += 1
                
            # Calculate total frames that would be rendered
            if camera.shotmaster_camera.use_custom_frames:
                frames = camera.shotmaster_camera.end_frame - camera.shotmaster_camera.start_frame + 1
            else:
                frames = context.scene.shotmaster_settings.master_end_frame - context.scene.shotmaster_settings.master_start_frame + 1
            
            stats['total_frames'] += frames
            
        # Calculate average render time
        if stats['total_renders'] > 0:
            stats['average_render_time'] = stats['total_render_time'] / stats['total_renders']
            
        return stats

# --------------------------------
# Operators
# --------------------------------

# Create a new camera
class SHOTMASTER_OT_create_camera(Operator):
    bl_idname = "shotmaster.create_camera"
    bl_label = "Create Camera"
    bl_description = "Create a new camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name: StringProperty(
        name="Group",
        description="Group to add the camera to",
        default=""
    )
    
    def execute(self, context):
        # Get the 3D cursor location for camera placement
        cursor_loc = context.scene.cursor.location
        
        # Get the current 3D view rotation
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        view_matrix = space.region_3d.view_matrix
                        # Convert view matrix to camera orientation (invert and adjust)
                        rot_matrix = view_matrix.to_3x3().transposed()
                        rotation = rot_matrix.to_euler()
                        # We need to rotate the camera 180 degrees around Z to face correct direction
                        rotation.rotate_axis('Z', math.radians(180.0))
                        
                        # Create camera at cursor with current view orientation
                        camera = ShotMasterManager.create_camera(
                            name=f"Shot_{len(ShotMasterManager.get_all_cameras())+1}",
                            location=cursor_loc,
                            rotation=rotation,
                            group=self.group_name
                        )
                        
                        # Set as active camera
                        ShotMasterManager.set_active_camera(camera)
                        
                        # Select the new camera
                        bpy.ops.object.select_all(action='DESELECT')
                        camera.select_set(True)
                        context.view_layer.objects.active = camera
                        
                        return {'FINISHED'}
        
        # Fallback if we couldn't get the view orientation
        camera = ShotMasterManager.create_camera(
            name=f"Shot_{len(ShotMasterManager.get_all_cameras())+1}",
            location=cursor_loc,
            group=self.group_name
        )
        
        # Set as active camera
        ShotMasterManager.set_active_camera(camera)
        
        # Select the new camera
        bpy.ops.object.select_all(action='DESELECT')
        camera.select_set(True)
        context.view_layer.objects.active = camera
        
        return {'FINISHED'}

# Duplicate a camera
class SHOTMASTER_OT_duplicate_camera(Operator):
    bl_idname = "shotmaster.duplicate_camera"
    bl_label = "Duplicate Camera"
    bl_description = "Duplicate the active camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        active_camera = context.scene.camera
        if not active_camera or active_camera.type != 'CAMERA':
            self.report({'ERROR'}, "No active camera to duplicate")
            return {'CANCELLED'}
            
        # Duplicate the camera
        new_camera = ShotMasterManager.duplicate_camera(active_camera)
        if not new_camera:
            self.report({'ERROR'}, "Failed to duplicate camera")
            return {'CANCELLED'}
            
        # Set as active camera
        ShotMasterManager.set_active_camera(new_camera)
        
        # Select the new camera
        bpy.ops.object.select_all(action='DESELECT')
        new_camera.select_set(True)
        context.view_layer.objects.active = new_camera
        
        return {'FINISHED'}

# Delete a camera
class SHOTMASTER_OT_delete_camera(Operator):
    bl_idname = "shotmaster.delete_camera"
    bl_label = "Delete Camera"
    bl_description = "Delete this camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, f"Could not find camera {self.camera_name}")
            return {'CANCELLED'}
        
        # If we're deleting the active camera, set a different one as active if available
        if context.scene.camera == camera:
            all_cameras = ShotMasterManager.get_all_cameras()
            if len(all_cameras) > 1:
                for cam in all_cameras:
                    if cam != camera:
                        context.scene.camera = cam
                        break
        
        # Delete the camera
        bpy.data.objects.remove(camera)
        
        return {'FINISHED'}

# Set a camera as active
class SHOTMASTER_OT_set_active_camera(Operator):
    bl_idname = "shotmaster.set_active_camera"
    bl_label = "Set as Active"
    bl_description = "Set this camera as the active scene camera"
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if camera and ShotMasterManager.set_active_camera(camera):
            return {'FINISHED'}
        self.report({'ERROR'}, f"Could not set {self.camera_name} as active camera")
        return {'CANCELLED'}

# Select a camera for editing
class SHOTMASTER_OT_select_camera(Operator):
    bl_idname = "shotmaster.select_camera"
    bl_label = "Select Camera"
    bl_description = "Select this camera for editing"
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if camera and camera.type == 'CAMERA':
            bpy.ops.object.select_all(action='DESELECT')
            camera.select_set(True)
            context.view_layer.objects.active = camera
            
            # Show properties panel
            camera.shotmaster_camera.show_properties = True
            
            return {'FINISHED'}
        
        self.report({'ERROR'}, f"Could not select {self.camera_name}")
        return {'CANCELLED'}

# Close camera properties panel
class SHOTMASTER_OT_close_properties(Operator):
    bl_idname = "shotmaster.close_properties"
    bl_label = "Close Properties"
    bl_description = "Close the camera properties panel"
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if camera and camera.type == 'CAMERA':
            camera.shotmaster_camera.show_properties = False
            return {'FINISHED'}
        
        return {'CANCELLED'}

# Render from camera
class SHOTMASTER_OT_render_from_camera(Operator):
    bl_idname = "shotmaster.render_camera"
    bl_label = "Render Camera"
    bl_description = "Render using this camera's settings"
    
    camera_name: StringProperty()
    render_animation: BoolProperty(default=False)
    is_viewport: BoolProperty(default=False)
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if camera and camera.type == 'CAMERA':
            if ShotMasterManager.render_from_camera(camera, self.render_animation, self.is_viewport):
                if self.render_animation:
                    if self.is_viewport:
                        self.report({'INFO'}, f"Successfully rendered viewport animation from {camera.name}")
                    else:
                        self.report({'INFO'}, f"Successfully rendered animation from {camera.name}")
                else:
                    if self.is_viewport:
                        self.report({'INFO'}, f"Successfully rendered viewport still from {camera.name}")
                    else:
                        self.report({'INFO'}, f"Successfully rendered still from {camera.name}")
                return {'FINISHED'}
        
        self.report({'ERROR'}, f"Could not render from {self.camera_name}")
        return {'CANCELLED'}

# Render all cameras
class SHOTMASTER_OT_render_all_cameras(Operator):
    bl_idname = "shotmaster.render_all_cameras"
    bl_label = "Render All Cameras"
    bl_description = "Render from all cameras"
    
    render_animation: BoolProperty(default=False)
    is_viewport: BoolProperty(default=False)
    
    def execute(self, context):
        cameras = ShotMasterManager.get_all_cameras()
        if not cameras:
            self.report({'WARNING'}, "No cameras found to render")
            return {'CANCELLED'}
            
        success_count = 0
        for camera in cameras:
            if ShotMasterManager.render_from_camera(camera, self.render_animation, self.is_viewport):
                success_count += 1
        
        if self.render_animation:
            if self.is_viewport:
                self.report({'INFO'}, f"Successfully rendered viewport animations for {success_count} of {len(cameras)} cameras")
            else:
                self.report({'INFO'}, f"Successfully rendered animations for {success_count} of {len(cameras)} cameras")
        else:
            if self.is_viewport:
                self.report({'INFO'}, f"Successfully rendered viewport stills for {success_count} of {len(cameras)} cameras")
            else:
                self.report({'INFO'}, f"Successfully rendered {success_count} of {len(cameras)} cameras")
            
        return {'FINISHED'}

# Render group cameras
class SHOTMASTER_OT_render_group_cameras(Operator):
    bl_idname = "shotmaster.render_group_cameras"
    bl_label = "Render Group"
    bl_description = "Render all cameras in this group"
    
    group_name: StringProperty()
    render_animation: BoolProperty(default=False)
    is_viewport: BoolProperty(default=False)
    
    def execute(self, context):
        cameras = ShotMasterManager.get_cameras_in_group(self.group_name)
        if not cameras:
            self.report({'WARNING'}, f"No cameras found in group {self.group_name}")
            return {'CANCELLED'}
            
        success_count = 0
        for camera in cameras:
            if ShotMasterManager.render_from_camera(camera, self.render_animation, self.is_viewport):
                success_count += 1
        
        if self.render_animation:
            if self.is_viewport:
                self.report({'INFO'}, f"Successfully rendered viewport animations for {success_count} of {len(cameras)} cameras in group {self.group_name}")
            else:
                self.report({'INFO'}, f"Successfully rendered animations for {success_count} of {len(cameras)} cameras in group {self.group_name}")
        else:
            if self.is_viewport:
                self.report({'INFO'}, f"Successfully rendered viewport stills for {success_count} of {len(cameras)} cameras in group {self.group_name}")
            else:
                self.report({'INFO'}, f"Successfully rendered stills for {success_count} of {len(cameras)} cameras in group {self.group_name}")
            
        return {'FINISHED'}

# View through camera
class SHOTMASTER_OT_view_through_camera(Operator):
    bl_idname = "shotmaster.view_through_camera"
    bl_label = "View Through"
    bl_description = "Set view to look through this camera"
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if camera and camera.type == 'CAMERA':
            # Set as active camera
            context.scene.camera = camera
            
            # Set 3D view to camera view
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.region_3d.view_perspective = 'CAMERA'
                            return {'FINISHED'}
        
        self.report({'ERROR'}, f"Could not view through {self.camera_name}")
        return {'CANCELLED'}

# Pick focus target
class SHOTMASTER_OT_pick_focus_target(Operator):
    bl_idname = "shotmaster.pick_focus_target"
    bl_label = "Pick Focus Target"
    bl_description = "Select an object to use as focus target"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        active_obj = context.active_object
        
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
            
        if not active_obj or active_obj == camera:
            self.report({'ERROR'}, "Select a valid target object first")
            return {'CANCELLED'}
            
        # Set the focus target
        camera.shotmaster_camera.focus_target = active_obj
        
        # Enable DOF if it's not already
        camera.data.dof.use_dof = True
        
        # Set focus to use target
        camera.data.dof.focus_object = active_obj
        
        self.report({'INFO'}, f"Set {active_obj.name} as focus target for {camera.name}")
        return {'FINISHED'}

# Clear focus target
class SHOTMASTER_OT_clear_focus_target(Operator):
    bl_idname = "shotmaster.clear_focus_target"
    bl_label = "Clear Focus Target"
    bl_description = "Clear the focus target for this camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
            
        # Clear the focus target
        camera.shotmaster_camera.focus_target = None
        camera.data.dof.focus_object = None
        
        self.report({'INFO'}, f"Cleared focus target for {camera.name}")
        return {'FINISHED'}

# Camera to view
class SHOTMASTER_OT_camera_to_view(Operator):
    bl_idname = "shotmaster.camera_to_view"
    bl_label = "Camera to View"
    bl_description = "Align camera to current 3D view"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
        
        # Find the current 3D view
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # Get view rotation and convert to camera orientation
                        view_matrix = space.region_3d.view_matrix
                        rot_matrix = view_matrix.to_3x3().transposed()
                        rotation = rot_matrix.to_euler()
                        # We need to rotate the camera 180 degrees around Z to face correct direction
                        rotation.rotate_axis('Z', math.radians(180.0))
                        
                        # Update camera orientation
                        camera.rotation_euler = rotation
                        
                        # Set camera as active
                        context.scene.camera = camera
                        
                        self.report({'INFO'}, f"Aligned camera {camera.name} to current view")
                        return {'FINISHED'}
        
        self.report({'ERROR'}, "Could not find 3D view to match")
        return {'CANCELLED'}

# Lock camera to cursor
class SHOTMASTER_OT_lock_camera_to_cursor(Operator):
    bl_idname = "shotmaster.lock_camera_to_cursor"
    bl_label = "Lock to 3D Cursor"
    bl_description = "Move camera to 3D cursor position"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
        
        # Move camera to 3D cursor position
        camera.location = context.scene.cursor.location
        
        # Set camera as active
        context.scene.camera = camera
        
        self.report({'INFO'}, f"Moved camera {camera.name} to 3D cursor")
        return {'FINISHED'}

# Rename camera
class SHOTMASTER_OT_rename_camera(Operator):
    bl_idname = "shotmaster.rename_camera"
    bl_label = "Rename Camera"
    bl_description = "Rename this camera"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    new_name: StringProperty(name="New Name", description="Enter a new name for the camera")
    
    def invoke(self, context, event):
        camera = bpy.data.objects.get(self.camera_name)
        if camera:
            self.new_name = camera.name
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
        
        if not self.new_name:
            self.report({'ERROR'}, "Camera name cannot be empty")
            return {'CANCELLED'}
        
        # Rename the camera
        old_name = camera.name
        camera.name = self.new_name
        
        self.report({'INFO'}, f"Renamed camera from {old_name} to {camera.name}")
        return {'FINISHED'}

# Toggle camera expanded
class SHOTMASTER_OT_toggle_camera_expanded(Operator):
    bl_idname = "shotmaster.toggle_camera_expanded"
    bl_label = "Toggle Camera Expanded"
    bl_description = "Toggle the expanded state of this camera"
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if camera and camera.type == 'CAMERA':
            camera.shotmaster_camera.is_expanded = not camera.shotmaster_camera.is_expanded
            return {'FINISHED'}
        return {'CANCELLED'}

# Add camera group
class SHOTMASTER_OT_add_camera_group(Operator):
    bl_idname = "shotmaster.add_camera_group"
    bl_label = "Add Camera Group"
    bl_description = "Add a new camera group"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name: StringProperty(
        name="Group Name",
        description="Name for the new camera group",
        default="Camera Group"
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        if not self.group_name:
            self.report({'ERROR'}, "Group name cannot be empty")
            return {'CANCELLED'}
        
        # Check if group already exists
        for group in context.scene.shotmaster_camera_groups:
            if group.name == self.group_name:
                self.report({'ERROR'}, f"Group '{self.group_name}' already exists")
                return {'CANCELLED'}
        
        # Create new group
        new_group = context.scene.shotmaster_camera_groups.add()
        new_group.name = self.group_name
        
        self.report({'INFO'}, f"Added camera group '{self.group_name}'")
        return {'FINISHED'}

# Remove camera group
class SHOTMASTER_OT_remove_camera_group(Operator):
    bl_idname = "shotmaster.remove_camera_group"
    bl_label = "Remove Camera Group"
    bl_description = "Remove this camera group"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name: StringProperty()
    
    def execute(self, context):
        # Find the group index
        group_index = -1
        for i, group in enumerate(context.scene.shotmaster_camera_groups):
            if group.name == self.group_name:
                group_index = i
                break
        
        if group_index == -1:
            self.report({'ERROR'}, f"Could not find group '{self.group_name}'")
            return {'CANCELLED'}
        
        # Unassign all cameras from this group
        for camera in ShotMasterManager.get_cameras_in_group(self.group_name):
            camera.shotmaster_camera.group = ""
        
        # Remove the group
        context.scene.shotmaster_camera_groups.remove(group_index)
        
        self.report({'INFO'}, f"Removed camera group '{self.group_name}'")
        return {'FINISHED'}

# Toggle group expanded
class SHOTMASTER_OT_toggle_group_expanded(Operator):
    bl_idname = "shotmaster.toggle_group_expanded"
    bl_label = "Toggle Group Expanded"
    bl_description = "Toggle the expanded state of this group"
    
    group_name: StringProperty()
    
    def execute(self, context):
        for group in context.scene.shotmaster_camera_groups:
            if group.name == self.group_name:
                group.is_expanded = not group.is_expanded
                return {'FINISHED'}
        return {'CANCELLED'}

# Assign camera to group
class SHOTMASTER_OT_assign_camera_to_group(Operator):
    bl_idname = "shotmaster.assign_camera_to_group"
    bl_label = "Assign to Group"
    bl_description = "Assign this camera to a group"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    group_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
        
        # Validate group exists if not empty
        if self.group_name:
            group_exists = False
            for group in context.scene.shotmaster_camera_groups:
                if group.name == self.group_name:
                    group_exists = True
                    break
            
            if not group_exists:
                self.report({'ERROR'}, f"Group '{self.group_name}' does not exist")
                return {'CANCELLED'}
        
        # Assign camera to group
        camera.shotmaster_camera.group = self.group_name
        
        if self.group_name:
            self.report({'INFO'}, f"Assigned camera '{camera.name}' to group '{self.group_name}'")
        else:
            self.report({'INFO'}, f"Removed camera '{camera.name}' from group")
        
        return {'FINISHED'}

# Assign to group popover
class SHOTMASTER_OT_assign_to_group_popover(Operator):
    bl_idname = "shotmaster.assign_to_group_popover"
    bl_label = "Assign to Group"
    bl_description = "Assign camera to a group"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)
    
    def draw(self, context):
        layout = self.layout
        camera = bpy.data.objects.get(self.camera_name)
        
        if not camera:
            layout.label(text="Camera not found")
            return
            
        # Current group
        box = layout.box()
        if camera.shotmaster_camera.group:
            box.label(text=f"Current Group: {camera.shotmaster_camera.group}")
        else:
            box.label(text="Not assigned to any group")
        
        # Remove from group option
        remove_op = layout.operator("shotmaster.assign_camera_to_group", text="Remove from Group")
        remove_op.camera_name = self.camera_name
        remove_op.group_name = ""
        
        layout.separator()
        layout.label(text="Assign to Group:")
        
        # List all available groups
        for group in context.scene.shotmaster_camera_groups:
            row = layout.row()
            op = row.operator("shotmaster.assign_camera_to_group", text=group.name)
            op.camera_name = self.camera_name
            op.group_name = group.name
            
            # Indicate current group
            if camera.shotmaster_camera.group == group.name:
                row.label(text="", icon='CHECKMARK')

# Edit group settings
class SHOTMASTER_OT_edit_group_settings(Operator):
    bl_idname = "shotmaster.edit_group_settings"
    bl_label = "Edit Group Settings"
    bl_description = "Edit group settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name: StringProperty()
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        
        # Find the group
        group = None
        for g in context.scene.shotmaster_camera_groups:
            if g.name == self.group_name:
                group = g
                break
        
        if not group:
            layout.label(text="Group not found")
            return
        
        # Group name
        layout.prop(group, "name", text="Group Name")
        
        # Group color
        layout.prop(group, "color", text="Group Color")
        
        # Group notes
        layout.prop(group, "notes", text="Notes")
        
        # Custom output path
        layout.prop(group, "use_custom_output_path", text="Custom Output Path")
        if group.use_custom_output_path:
            layout.prop(group, "output_path", text="Output Path")
        else:
            layout.label(text="Using Master Output Path")
            
        # Render settings
        box = layout.box()
        box.label(text="Render Settings:")
        box.prop(group, "use_custom_render_settings", text="Custom Render Settings")
        
        if group.use_custom_render_settings:
            # Engine
            box.prop(group, "render_engine", text="Render Engine")
            
            # Engine-specific settings
            if group.render_engine == 'CYCLES':
                box.prop(group, "cycles_samples", text="Cycles Samples")
            elif group.render_engine == 'BLENDER_EEVEE':
                box.prop(group, "eevee_samples", text="Eevee Samples")
            
            # Resolution
            res_box = box.box()
            res_box.prop(group, "use_custom_resolution", text="Custom Resolution")
            
            if group.use_custom_resolution:
                res_row = res_box.row(align=True)
                res_row.prop(group, "resolution_x", text="Width")
                res_row.prop(group, "resolution_y", text="Height")
                res_box.prop(group, "resolution_percentage", text="Resolution %")
                
        # View layer
        layer_box = layout.box()
        layer_box.label(text="View Layer Settings:")
        layer_box.prop(group, "use_custom_view_layer", text="Custom View Layer")
        
        if group.use_custom_view_layer:
            # Get all view layers
            view_layers = [(layer.name, layer.name, "") for layer in context.scene.view_layers]
            layer_box.prop_search(group, "view_layer", bpy.context.scene, "view_layers", text="View Layer")

# Add render pass
class SHOTMASTER_OT_add_render_pass(Operator):
    bl_idname = "shotmaster.add_render_pass"
    bl_label = "Add Render Pass"
    bl_description = "Add a new render pass"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
        
        new_pass = camera.shotmaster_camera.render_passes.add()
        
        # Set default name based on number of passes
        new_pass.name = f"pass_{len(camera.shotmaster_camera.render_passes)}"
        new_pass.pass_type = 'BEAUTY'
        new_pass.enabled = True
        
        # Set as active
        camera.shotmaster_camera.active_pass_index = len(camera.shotmaster_camera.render_passes) - 1
        
        return {'FINISHED'}

# Delete render pass
class SHOTMASTER_OT_delete_render_pass(Operator):
    bl_idname = "shotmaster.delete_render_pass"
    bl_label = "Delete Render Pass"
    bl_description = "Delete selected render pass"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
        
        if len(camera.shotmaster_camera.render_passes) <= 0:
            self.report({'ERROR'}, "No render passes to delete")
            return {'CANCELLED'}
        
        # Delete the active pass
        index = camera.shotmaster_camera.active_pass_index
        camera.shotmaster_camera.render_passes.remove(index)
        
        # Adjust the active index if needed
        if index >= len(camera.shotmaster_camera.render_passes):
            camera.shotmaster_camera.active_pass_index = max(0, len(camera.shotmaster_camera.render_passes) - 1)
        
        return {'FINISHED'}

# Move render pass up
class SHOTMASTER_OT_move_render_pass_up(Operator):
    bl_idname = "shotmaster.move_render_pass_up"
    bl_label = "Move Render Pass Up"
    bl_description = "Move render pass up in the list"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
        
        index = camera.shotmaster_camera.active_pass_index
        if index <= 0 or index >= len(camera.shotmaster_camera.render_passes):
            return {'CANCELLED'}
        
        # Swap with previous item
        camera.shotmaster_camera.render_passes.move(index, index - 1)
        camera.shotmaster_camera.active_pass_index -= 1
        
        return {'FINISHED'}

# Move render pass down
class SHOTMASTER_OT_move_render_pass_down(Operator):
    bl_idname = "shotmaster.move_render_pass_down"
    bl_label = "Move Render Pass Down"
    bl_description = "Move render pass down in the list"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, "Invalid camera")
            return {'CANCELLED'}
        
        index = camera.shotmaster_camera.active_pass_index
        if index < 0 or index >= len(camera.shotmaster_camera.render_passes) - 1:
            return {'CANCELLED'}
        
        # Swap with next item
        camera.shotmaster_camera.render_passes.move(index, index + 1)
        camera.shotmaster_camera.active_pass_index += 1
        
        return {'FINISHED'}

# Show camera statistics
class SHOTMASTER_OT_show_statistics(Operator):
    bl_idname = "shotmaster.show_statistics"
    bl_label = "ShotMaster Statistics"
    bl_description = "Show statistics about all cameras in the scene"
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)
    
    def draw(self, context):
        layout = self.layout
        
        # Get statistics
        stats = ShotMasterManager.get_camera_statistics(context)
        
        # Overview
        overview_box = layout.box()
        overview_box.label(text="Overview", icon='INFO')
        
        row = overview_box.row()
        row.label(text=f"Total Cameras: {stats['total_cameras']}")
        row.label(text=f"Total Groups: {stats['total_groups']}")
        
        # Render statistics
        render_box = layout.box()
        render_box.label(text="Render Statistics", icon='RENDER_STILL')
        
        row = render_box.row()
        row.label(text=f"Total Renders: {stats['total_renders']}")
        
        # Format render time nicely
        total_time = datetime.timedelta(seconds=int(stats['total_render_time']))
        avg_time = "N/A" if stats['total_renders'] == 0 else f"{stats['average_render_time']:.2f} seconds"
        last_time = f"{stats['last_render_time']:.2f} seconds"
        
        row = render_box.row()
        row.label(text=f"Total Render Time: {total_time}")
        
        row = render_box.row()
        row.label(text=f"Average Render Time: {avg_time}")
        row.label(text=f"Last Render Time: {last_time}")
        
        row = render_box.row()
        row.label(text=f"Total Frames: {stats['total_frames']}")
        
        # Cameras by group
        group_box = layout.box()
        group_box.label(text="Cameras by Group", icon='GROUP')
        
        for group, count in stats['cameras_by_group'].items():
            if count > 0:  # Only show groups with cameras
                row = group_box.row()
                row.label(text=f"{group}: {count} cameras")
        
        # Render engines
        engine_box = layout.box()
        engine_box.label(text="Render Engines", icon='SCENE')
        
        for engine, count in stats['render_engines'].items():
            if count > 0:  # Only show used engines
                row = engine_box.row()
                row.label(text=f"{engine}: {count} cameras")
        
        # Shot types and sizes (if there are any)
        if stats['shot_types'] or stats['shot_sizes']:
            shot_box = layout.box()
            shot_box.label(text="Shot Information", icon='CAMERA_DATA')
            
            col = shot_box.column()
            col.scale_y = 0.7
            
            # Shot types
            col.label(text="Shot Types:")
            for type_id, count in stats['shot_types'].items():
                # Get readable name from enum
                type_name = next((item[1] for item in SHOT_TYPES if item[0] == type_id), type_id)
                col.label(text=f"  • {type_name}: {count}")
            
            col.separator()
            
            # Shot sizes
            col.label(text="Shot Sizes:")
            for size_id, count in stats['shot_sizes'].items():
                # Get readable name from enum
                size_name = next((item[1] for item in SHOT_SIZES if item[0] == size_id), size_id)
                col.label(text=f"  • {size_name}: {count}")
        
        # Equipment
        if stats['equipment']:
            equipment_box = layout.box()
            equipment_box.label(text="Equipment", icon='TOOL_SETTINGS')
            
            col = equipment_box.column()
            col.scale_y = 0.7
            
            for equip_id, count in stats['equipment'].items():
                # Get readable name from enum
                equip_name = next((item[1] for item in EQUIPMENT_TYPES if item[0] == equip_id), equip_id)
                col.label(text=f"  • {equip_name}: {count}")

# --------------------------------
# UI Helper Functions
# --------------------------------

# Helper function to draw camera item in UI
def draw_camera_item(self, context, layout, camera):
    # Get the camera color (either from camera or its group)
    camera_color = camera.shotmaster_camera.color
    
    # If camera is in a group, get the group's color
    group_name = camera.shotmaster_camera.group
    group_color = None
    
    if group_name:
        for group in context.scene.shotmaster_camera_groups:
            if group.name == group_name:
                group_color = group.color
                break
    
    # Create box with color customization
    box = layout.box()
    
    # Use group color as background if available, otherwise use camera color
    if group_color:
        box.use_property_split = False
        box.use_property_decorate = False
        # We can't directly set the box background color in Blender UI
        # but we can show a visual indicator of the group color
    
    # Camera header row with name and status
    row = box.row(align=True)
    
    is_active = (context.scene.camera == camera)
    icon = 'OUTLINER_OB_CAMERA' if not is_active else 'VIEW_CAMERA'
    
    # Expand/collapse toggle
    expand_icon = 'TRIA_DOWN' if camera.shotmaster_camera.is_expanded else 'TRIA_RIGHT'
    op = row.operator("shotmaster.toggle_camera_expanded", text="", icon=expand_icon, emboss=False)
    op.camera_name = camera.name
    
    # Set active button/indicator
    if not is_active:
        op = row.operator("shotmaster.set_active_camera", text="", icon='RADIOBUT_OFF')
        op.camera_name = camera.name
    else:
        row.label(text="", icon='RADIOBUT_ON')
    
    # Small color square
    color_row = row.row()
    color_row.scale_x = 0.3
    color_row.scale_y = 0.8
    color_row.prop(camera.shotmaster_camera, "color", text="")
    
    # Camera name (can be renamed by clicking button)
    rename_op = row.operator("shotmaster.rename_camera", text=camera.name, icon=icon)
    rename_op.camera_name = camera.name
    
    # Group assignment
    group_op = row.operator("shotmaster.assign_to_group_popover", text="", icon='GROUP')
    group_op.camera_name = camera.name
    
    # Quick actions
    row = box.row(align=True)
    
    # View through camera
    op = row.operator("shotmaster.view_through_camera", text="", icon='RESTRICT_VIEW_OFF')
    op.camera_name = camera.name
    
    # Camera to View button
    op = row.operator("shotmaster.camera_to_view", text="", icon='CAMERA_DATA')
    op.camera_name = camera.name
    
    # Lock to 3D Cursor button
    op = row.operator("shotmaster.lock_camera_to_cursor", text="", icon='PIVOT_CURSOR')
    op.camera_name = camera.name
    
    # Render buttons
    op = row.operator("shotmaster.render_camera", text="", icon='RENDER_STILL')
    op.camera_name = camera.name
    op.render_animation = False
    op.is_viewport = False
    
    op = row.operator("shotmaster.render_camera", text="", icon='RENDER_ANIMATION')
    op.camera_name = camera.name
    op.render_animation = True
    op.is_viewport = False
    
    # Viewport render buttons
    op = row.operator("shotmaster.render_camera", text="", icon='RESTRICT_VIEW_OFF')
    op.camera_name = camera.name
    op.render_animation = False
    op.is_viewport = True
    
    op = row.operator("shotmaster.render_camera", text="", icon='TRACKER')
    op.camera_name = camera.name
    op.render_animation = True
    op.is_viewport = True
    
    # Select button
    op = row.operator("shotmaster.select_camera", text="", icon='RESTRICT_SELECT_OFF')
    op.camera_name = camera.name
    
    # Delete button
    op = row.operator("shotmaster.delete_camera", text="", icon='X')
    op.camera_name = camera.name
    
    # Only show details if expanded
    if camera.shotmaster_camera.is_expanded:
        # Camera lens info
        row = box.row()
        row.label(text=f"Lens: {camera.data.lens:.1f}mm")
        
        # Show DOF info
        if camera.data.dof.use_dof:
            dof_distance = ShotMasterManager.calculate_dof_distance(camera)
            row.label(text=f"DOF: {dof_distance}")
        else:
            row.label(text="DOF: Disabled")
        
        # Sensor size
        row = box.row()
        sensor_name = get_sensor_name(camera.shotmaster_camera.sensor_size)
        row.label(text=f"Sensor: {sensor_name}")
        
        # White balance
        row = box.row()
        wb_preset = next((item[1] for item in WHITE_BALANCE_PRESETS if item[0] == camera.shotmaster_camera.white_balance_preset), "Custom")
        row.label(text=f"White Bal: {wb_preset} ({camera.shotmaster_camera.white_balance_temp}K)")
        
        # Focus target (if applicable)
        if camera.shotmaster_camera.focus_target:
            row = box.row()
            row.label(text=f"Focus: {camera.shotmaster_camera.focus_target.name}")
            
            # Clear focus target button
            op = row.operator("shotmaster.clear_focus_target", text="", icon='X')
            op.camera_name = camera.name
        elif camera.data.dof.use_dof:
            row = box.row()
            row.label(text=f"Focus Distance: {camera.data.dof.focus_distance:.2f}m")
        
        # Shot info
        row = box.row()
        shot_size = next((item[1] for item in SHOT_SIZES if item[0] == camera.shotmaster_camera.shot_size), "Unknown")
        shot_type = next((item[1] for item in SHOT_TYPES if item[0] == camera.shotmaster_camera.shot_type), "Unknown")
        row.label(text=f"Shot: {shot_size} ({shot_type})")
        
        # Animation settings summary
        row = box.row()
        if camera.shotmaster_camera.use_custom_frames:
            row.label(text=f"Frames: {camera.shotmaster_camera.start_frame}-{camera.shotmaster_camera.end_frame}")
        else:
            row.label(text="Using Master Frame Range")
        
        # Output path summary
        path_row = box.row()
        if camera.shotmaster_camera.use_custom_output_path:
            path_row.label(text="Custom Output Path")
        elif camera.shotmaster_camera.group:
            # Check if group has custom path
            group_has_custom = False
            for group in context.scene.shotmaster_camera_groups:
                if group.name == camera.shotmaster_camera.group and group.use_custom_output_path:
                    group_has_custom = True
                    break
            
            if group_has_custom:
                path_row.label(text="Using Group Output Path")
            else:
                path_row.label(text="Using Master Output Path")
        else:
            path_row.label(text="Using Master Output Path")
        
        # Show full properties if selected
        if camera == context.object and camera.type == 'CAMERA' and camera.shotmaster_camera.show_properties:
            prop_box = box.box()
            
            # Add close button at top of properties
            close_row = prop_box.row()
            close_row.alignment = 'RIGHT'
            op = close_row.operator("shotmaster.close_properties", text="Close Properties", icon='X')
            op.camera_name = camera.name
            
            # Tabs for different property categories
            tab_row = prop_box.row(align=True)
            tab_row.prop_enum(camera.shotmaster_camera, "active_property_tab", 'CAMERA', text="Camera")
            tab_row.prop_enum(camera.shotmaster_camera, "active_property_tab", 'RENDER', text="Render")
            tab_row.prop_enum(camera.shotmaster_camera, "active_property_tab", 'OUTPUT', text="Output")
            tab_row.prop_enum(camera.shotmaster_camera, "active_property_tab", 'NOTES', text="Notes")
            tab_row.prop_enum(camera.shotmaster_camera, "active_property_tab", 'LAYERS', text="Layers")
            
            # Camera settings tab
            if camera.shotmaster_camera.active_property_tab == 'CAMERA':
                cam_box = prop_box.box()
                
                # Lens settings
                lens_row = cam_box.row()
                lens_row.prop(camera.data, "lens", text="Focal Length")
                
                # Sensor settings
                sensor_row = cam_box.row()
                sensor_row.prop(camera.shotmaster_camera, "sensor_size", text="Sensor Preset")
                
                # White balance settings
                wb_row = cam_box.row()
                wb_row.prop(camera.shotmaster_camera, "white_balance_preset", text="White Balance")
                
                if camera.shotmaster_camera.white_balance_preset == 'CUSTOM':
                    wb_temp_row = cam_box.row()
                    wb_temp_row.prop(camera.shotmaster_camera, "white_balance_temp", text="Color Temp (K)")
                
                # DOF settings
                dof_row = cam_box.row()
                dof_row.prop(camera.data.dof, "use_dof", text="Depth of Field")
                
                if camera.data.dof.use_dof:
                    if not camera.data.dof.focus_object:
                        cam_box.prop(camera.data.dof, "focus_distance", text="Focus Distance")
                        
                    focus_row = cam_box.row()
                    op = focus_row.operator("shotmaster.pick_focus_target", text="Pick Focus Target")
                    op.camera_name = camera.name
                    
                    # Show aperture settings
                    cam_box.prop(camera.data.dof, "aperture_fstop", text="F-Stop")
                
                # Passepartout settings
                passepartout_row = cam_box.row()
                passepartout_row.prop(camera.data, "passepartout_alpha", text="Passepartout")
                
            # Render settings tab
            elif camera.shotmaster_camera.active_property_tab == 'RENDER':
                render_box = prop_box.box()
                
                # Custom render settings toggle
                render_box.prop(camera.shotmaster_camera, "use_custom_render_settings", text="Custom Render Settings")
                
                if camera.shotmaster_camera.use_custom_render_settings:
                    # Engine selection
                    render_box.prop(camera.shotmaster_camera, "render_engine", text="Engine")
                    
                    # Engine-specific settings
                    if camera.shotmaster_camera.render_engine == 'CYCLES':
                        render_box.prop(camera.shotmaster_camera, "cycles_samples", text="Cycles Samples")
                    elif camera.shotmaster_camera.render_engine == 'BLENDER_EEVEE':
                        render_box.prop(camera.shotmaster_camera, "eevee_samples", text="Eevee Samples")
                    
                    # Resolution settings
                    res_box = render_box.box()
                    res_box.label(text="Resolution:")
                    res_box.prop(camera.shotmaster_camera, "use_custom_resolution", text="Custom Resolution")
                    
                    if camera.shotmaster_camera.use_custom_resolution:
                        res_row = res_box.row(align=True)
                        res_row.prop(camera.shotmaster_camera, "resolution_x", text="Width")
                        res_row.prop(camera.shotmaster_camera, "resolution_y", text="Height")
                        res_box.prop(camera.shotmaster_camera, "resolution_percentage", text="Resolution %")
                    else:
                        # Show which resolution is being used (group or master)
                        group_name = camera.shotmaster_camera.group
                        if group_name:
                            for group in context.scene.shotmaster_camera_groups:
                                if group.name == group_name and group.use_custom_render_settings and group.use_custom_resolution:
                                    res_box.label(text=f"Using Group: {group.resolution_x}×{group.resolution_y} ({group.resolution_percentage}%)")
                                    break
                            else:
                                res_box.label(text=f"Using Master: {context.scene.shotmaster_settings.master_resolution_x}×{context.scene.shotmaster_settings.master_resolution_y} ({context.scene.shotmaster_settings.master_resolution_percentage}%)")
                        else:
                            res_box.label(text=f"Using Master: {context.scene.shotmaster_settings.master_resolution_x}×{context.scene.shotmaster_settings.master_resolution_y} ({context.scene.shotmaster_settings.master_resolution_percentage}%)")
                
                # Render passes
                passes_box = render_box.box()
                passes_box.label(text="Render Passes:")
                passes_box.prop(camera.shotmaster_camera, "use_render_passes", text="Use Render Passes")
                
                if camera.shotmaster_camera.use_render_passes:
                    # List all passes
                    list_row = passes_box.row()
                    list_row.template_list("UI_UL_list", "render_passes", camera.shotmaster_camera, "render_passes", 
                                        camera.shotmaster_camera, "active_pass_index")
                    
                    # Add pass management buttons
                    list_ops = list_row.column(align=True)
                    add_op = list_ops.operator("shotmaster.add_render_pass", text="", icon='ADD')
                    add_op.camera_name = camera.name
                    
                    del_op = list_ops.operator("shotmaster.delete_render_pass", text="", icon='REMOVE')
                    del_op.camera_name = camera.name
                    
                    list_ops.separator()
                    
                    up_op = list_ops.operator("shotmaster.move_render_pass_up", text="", icon='TRIA_UP')
                    up_op.camera_name = camera.name
                    
                    down_op = list_ops.operator("shotmaster.move_render_pass_down", text="", icon='TRIA_DOWN')
                    down_op.camera_name = camera.name
                    
                    # Show active pass properties
                    if len(camera.shotmaster_camera.render_passes) > 0 and camera.shotmaster_camera.active_pass_index >= 0 and camera.shotmaster_camera.active_pass_index < len(camera.shotmaster_camera.render_passes):
                        active_pass = camera.shotmaster_camera.render_passes[camera.shotmaster_camera.active_pass_index]
                        
                        pass_box = passes_box.box()
                        pass_box.prop(active_pass, "enabled", text="Enabled")
                        pass_box.prop(active_pass, "pass_type", text="Pass Type")
                        pass_box.prop(active_pass, "name", text="Pass Name")
            
            # Output settings tab
            elif camera.shotmaster_camera.active_property_tab == 'OUTPUT':
                output_box = prop_box.box()
                
                # Animation settings
                anim_box = output_box.box()
                anim_box.label(text="Animation Settings:")
                
                # Override master frame range
                override_row = anim_box.row()
                override_row.prop(camera.shotmaster_camera, "use_custom_frames", text="Custom Frame Range")
                
                if camera.shotmaster_camera.use_custom_frames:
                    frame_row = anim_box.row(align=True)
                    frame_row.prop(camera.shotmaster_camera, "start_frame", text="Start")
                    frame_row.prop(camera.shotmaster_camera, "end_frame", text="End")
                else:
                    # Show master frame range
                    master_row = anim_box.row()
                    master_row.label(text=f"Using Master: {context.scene.shotmaster_settings.master_start_frame}-{context.scene.shotmaster_settings.master_end_frame}")
                
                # Output path options
                path_box = output_box.box()
                path_box.label(text="Output Path:")
                path_box.prop(camera.shotmaster_camera, "use_custom_output_path", text="Custom Output Path")
                
                if camera.shotmaster_camera.use_custom_output_path:
                    path_row = path_box.row()
                    path_row.prop(camera.shotmaster_camera, "output_path", text="Path")
                else:
                    # Show which path will be used
                    if camera.shotmaster_camera.group:
                        # Check if group has custom path
                        group_has_custom = False
                        group_path = ""
                        for group in context.scene.shotmaster_camera_groups:
                            if group.name == camera.shotmaster_camera.group and group.use_custom_output_path:
                                group_has_custom = True
                                group_path = group.output_path
                                break
                        
                        if group_has_custom:
                            path_row = path_box.row()
                            path_row.label(text=f"Using Group Path: {group_path if group_path else 'Not set'}")
                        else:
                            path_row = path_box.row()
                            path_row.label(text=f"Using Master Path: {context.scene.shotmaster_settings.master_output_path}")
                    else:
                        path_row = path_box.row()
                        path_row.label(text=f"Using Master Path: {context.scene.shotmaster_settings.master_output_path}")
                
                # File format settings
                format_box = output_box.box()
                format_box.label(text="File Format:")
                
                name_row = format_box.row()
                name_row.prop(camera.shotmaster_camera, "filename", text="Base Name")
                
                format_row = format_box.row()
                format_row.prop(camera.shotmaster_camera, "file_format", text="Format")
                
                # Show final output paths
                path_info = output_box.box()
                path_info.label(text="Output Locations:")
                
                # Still path
                still_path = ShotMasterManager.get_camera_output_path(camera, False)
                path_info.label(text=f"Still: {still_path}")
                
                # Animation path
                anim_path = ShotMasterManager.get_camera_output_path(camera, True)
                path_info.label(text=f"Animation: {anim_path}")
                
                # Render passes paths (if enabled)
                if camera.shotmaster_camera.use_render_passes and len(camera.shotmaster_camera.render_passes) > 0:
                    for pass_item in camera.shotmaster_camera.render_passes:
                        if pass_item.enabled:
                            pass_path = ShotMasterManager.get_camera_output_path(camera, False, pass_item.name)
                            path_info.label(text=f"{pass_item.name}: {pass_path}")
            
            # Notes tab
            elif camera.shotmaster_camera.active_property_tab == 'NOTES':
                notes_box = prop_box.box()
                
                # General notes
                notes_box.label(text="General Notes:")
                notes_box.prop(camera.shotmaster_camera, "notes", text="")
                
                # Shot information
                shot_box = notes_box.box()
                shot_box.label(text="Shot Information:")
                
                shot_box.prop(camera.shotmaster_camera, "shot_size", text="Shot Size")
                shot_box.prop(camera.shotmaster_camera, "shot_type", text="Shot Type")
                shot_box.prop(camera.shotmaster_camera, "shot_movement", text="Movement Details")
                
                # Equipment information
                equip_box = notes_box.box()
                equip_box.label(text="Equipment:")
                
                equip_box.prop(camera.shotmaster_camera, "equipment", text="Equipment Type")
                equip_box.prop(camera.shotmaster_camera, "equipment_notes", text="Equipment Notes")
            
            # Layers tab
            elif camera.shotmaster_camera.active_property_tab == 'LAYERS':
                layers_box = prop_box.box()
                
                # View layer selection
                layers_box.label(text="View Layer:")
                layers_box.prop(camera.shotmaster_camera, "use_custom_view_layer", text="Custom View Layer")
                
                if camera.shotmaster_camera.use_custom_view_layer:
                    layers_box.prop_search(camera.shotmaster_camera, "view_layer", bpy.context.scene, "view_layers", text="View Layer")
                else:
                    # Show which view layer is being used
                    group_name = camera.shotmaster_camera.group
                    if group_name:
                        for group in context.scene.shotmaster_camera_groups:
                            if group.name == group_name and group.use_custom_view_layer:
                                layers_box.label(text=f"Using Group Layer: {group.view_layer}")
                                break
                        else:
                            layers_box.label(text="Using Default View Layer")
                    else:
                        layers_box.label(text="Using Default View Layer")
                
                # Collections visibility
                # This is more complex as we'd need to handle per-collection visibility
                # For now, just add a placeholder
                layers_box.label(text="Collection Visibility:")
                layers_box.label(text="(Collection visibility control coming soon)")
        else:
            # Select to edit button for not-selected cameras
            row = box.row()
            row.operator("shotmaster.select_camera", text="Select to Edit Properties").camera_name = camera.name

class SHOTMASTER_UL_cameras(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if item:
                layout.label(text=item.name, icon='CAMERA_DATA')
            else:
                layout.label(text="", icon='CAMERA_DATA')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='CAMERA_DATA')

class SHOTMASTER_PT_manager(Panel):
    bl_label = "ShotMaster"
    bl_idname = "SHOTMASTER_PT_manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ShotMaster'
    
    def draw(self, context):
        layout = self.layout
        
        # Add statistics and buttons at the top
        top_row = layout.row(align=True)
        top_row.operator("shotmaster.show_statistics", text="Statistics", icon='INFO')
        
        # Add advanced toggle
        top_row.prop(context.scene.shotmaster_settings, "show_advanced_options", text="", icon='PREFERENCES')
        
        # Master settings (collapsible)
        box = layout.box()
        box.label(text="Master Settings:", icon='SCENE')
        
        # Master output path
        output_row = box.row()
        output_row.prop(context.scene.shotmaster_settings, "master_output_path", text="Output Path")
        
        # Animation frame range
        row = box.row(align=True)
        row.prop(context.scene.shotmaster_settings, "master_start_frame", text="Start")
        row.prop(context.scene.shotmaster_settings, "master_end_frame", text="End")
        
        # Show advanced render settings if enabled
        if context.scene.shotmaster_settings.show_advanced_options:
            # Resolution
            res_row = box.row(align=True)
            res_row.prop(context.scene.shotmaster_settings, "master_resolution_x", text="Width")
            res_row.prop(context.scene.shotmaster_settings, "master_resolution_y", text="Height")
            box.prop(context.scene.shotmaster_settings, "master_resolution_percentage", text="Resolution %")
            
            # Engine settings
            box.prop(context.scene.shotmaster_settings, "master_render_engine", text="Engine")
            
            # Engine-specific settings
            if context.scene.shotmaster_settings.master_render_engine == 'CYCLES':
                box.prop(context.scene.shotmaster_settings, "master_cycles_samples", text="Cycles Samples")
            elif context.scene.shotmaster_settings.master_render_engine == 'BLENDER_EEVEE':
                box.prop(context.scene.shotmaster_settings, "master_eevee_samples", text="Eevee Samples")
        
        # Camera actions row
        action_box = layout.box()
        action_box.label(text="Camera Actions:", icon='CAMERA_DATA')
        
        row = action_box.row(align=True)
        row.operator("shotmaster.create_camera", text="Add Camera", icon='ADD')
        row.operator("shotmaster.duplicate_camera", text="Duplicate", icon='DUPLICATE')
        
        # Render actions
        render_row = action_box.row(align=True)
        render_row.operator("shotmaster.render_all_cameras", text="Render Stills", icon='RENDER_STILL')
        render_row.operator("shotmaster.render_all_cameras", text="Animations", icon='RENDER_ANIMATION').render_animation = True
        
        # Viewport render actions
        if context.scene.shotmaster_settings.show_advanced_options:
            viewport_row = action_box.row(align=True)
            viewport_render_op = viewport_row.operator("shotmaster.render_all_cameras", text="Viewport Stills", icon='RESTRICT_VIEW_OFF')
            viewport_render_op.is_viewport = True
            
            viewport_anim_op = viewport_row.operator("shotmaster.render_all_cameras", text="Viewport Anim", icon='TRACKER')
            viewport_anim_op.render_animation = True
            viewport_anim_op.is_viewport = True
        
        # Group management
        group_box = layout.box()
        group_title_row = group_box.row()
        group_title_row.label(text="Camera Groups:", icon='GROUP')
        group_title_row.operator("shotmaster.add_camera_group", text="", icon='ADD')
        
        # Display groups and their cameras
        for group in context.scene.shotmaster_camera_groups:
            # Create a box with the group's color
            group_box_outer = group_box.box()
            
            # Group header with expand/collapse button
            header_row = group_box_outer.row(align=True)
            
            # Group header with expand/collapse button
            expand_icon = 'TRIA_DOWN' if group.is_expanded else 'TRIA_RIGHT'
            op = header_row.operator("shotmaster.toggle_group_expanded", text="", icon=expand_icon, emboss=False)
            op.group_name = group.name
            
            # Small color square
            color_row = header_row.row()
            color_row.scale_x = 0.3
            color_row.scale_y = 0.8
            color_row.prop(group, "color", text="")
            
            # Group name
            header_row.label(text=group.name)
            
            # Group actions
            action_row = header_row.row(align=True)
            
            # Add camera to this group
            op = action_row.operator("shotmaster.create_camera", text="", icon='CAMERA_DATA')
            op.group_name = group.name
            
            # Edit group settings
            op = action_row.operator("shotmaster.edit_group_settings", text="", icon='PREFERENCES')
            op.group_name = group.name
            
            # Render all cameras in this group
            render_op = action_row.operator("shotmaster.render_group_cameras", text="", icon='RENDER_STILL')
            render_op.group_name = group.name
            
            # Render all animations in this group
            anim_op = action_row.operator("shotmaster.render_group_cameras", text="", icon='RENDER_ANIMATION')
            anim_op.group_name = group.name
            anim_op.render_animation = True
            
            # Delete group
            delete_op = action_row.operator("shotmaster.remove_camera_group", text="", icon='X')
            delete_op.group_name = group.name
            
            # Show notes if they exist
            if group.notes:
                note_row = group_box_outer.row()
                note_row.label(text=f"Notes: {group.notes}")
            
            # Show custom output path if enabled
            if group.use_custom_output_path:
                path_row = group_box_outer.row()
                path_row.label(text=f"Output: {group.output_path if group.output_path else 'Not set'}")
            
            # Show custom render settings if enabled
            if group.use_custom_render_settings and context.scene.shotmaster_settings.show_advanced_options:
                render_row = group_box_outer.row()
                render_row.label(text=f"Engine: {group.render_engine}")
                
                if group.use_custom_resolution:
                    res_row = group_box_outer.row()
                    res_row.label(text=f"Resolution: {group.resolution_x}×{group.resolution_y} ({group.resolution_percentage}%)")
            
            # Show cameras in this group if expanded
            if group.is_expanded:
                cameras = ShotMasterManager.get_cameras_in_group(group.name)
                if not cameras:
                    group_box_outer.label(text="No cameras in this group", icon='INFO')
                else:
                    for camera in cameras:
                        draw_camera_item(self, context, group_box_outer, camera)
        
        # Display ungrouped cameras
        layout.separator()
        ungrouped_box = layout.box()
        ungrouped_box.label(text="Ungrouped Cameras:", icon='OUTLINER_OB_CAMERA')
        
        cameras = ShotMasterManager.get_ungrouped_cameras()
        if not cameras:
            ungrouped_box.label(text="No ungrouped cameras", icon='INFO')
        else:
            for camera in cameras:
                draw_camera_item(self, context, ungrouped_box, camera)

# Registration
classes = (
    # Property groups
    RenderPass,
    CameraGroup,
    ShotMasterCamera,
    ShotMasterSettings,
    
    # Operators
    SHOTMASTER_OT_create_camera,
    SHOTMASTER_OT_duplicate_camera,
    SHOTMASTER_OT_delete_camera,
    SHOTMASTER_OT_set_active_camera,
    SHOTMASTER_OT_select_camera,
    SHOTMASTER_OT_close_properties,
    SHOTMASTER_OT_render_from_camera,
    SHOTMASTER_OT_render_all_cameras,
    SHOTMASTER_OT_render_group_cameras,
    SHOTMASTER_OT_view_through_camera,
    SHOTMASTER_OT_pick_focus_target,
    SHOTMASTER_OT_clear_focus_target,
    SHOTMASTER_OT_camera_to_view,
    SHOTMASTER_OT_lock_camera_to_cursor,
    SHOTMASTER_OT_rename_camera,
    SHOTMASTER_OT_toggle_camera_expanded,
    SHOTMASTER_OT_add_camera_group,
    SHOTMASTER_OT_remove_camera_group,
    SHOTMASTER_OT_toggle_group_expanded,
    SHOTMASTER_OT_assign_camera_to_group,
    SHOTMASTER_OT_assign_to_group_popover,
    SHOTMASTER_OT_edit_group_settings,
    SHOTMASTER_OT_add_render_pass,
    SHOTMASTER_OT_delete_render_pass,
    SHOTMASTER_OT_move_render_pass_up,
    SHOTMASTER_OT_move_render_pass_down,
    SHOTMASTER_OT_show_statistics,
    
    # UI classes
    SHOTMASTER_UL_cameras,
    SHOTMASTER_PT_manager,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Error registering {cls.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    # Register custom properties
    bpy.types.Object.shotmaster_camera = PointerProperty(type=ShotMasterCamera)
    bpy.types.Scene.shotmaster_camera_groups = CollectionProperty(type=CameraGroup)
    bpy.types.Scene.shotmaster_settings = PointerProperty(type=ShotMasterSettings)

def unregister():
    # Unregister custom properties
    if hasattr(bpy.types.Scene, "shotmaster_settings"):
        del bpy.types.Scene.shotmaster_settings
    if hasattr(bpy.types.Scene, "shotmaster_camera_groups"):
        del bpy.types.Scene.shotmaster_camera_groups
    if hasattr(bpy.types.Object, "shotmaster_camera"):
        del bpy.types.Object.shotmaster_camera
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering {cls.__name__}: {e}")

if __name__ == "__main__":
    register()
                