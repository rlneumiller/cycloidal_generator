"""Create cycloidal gearbox"""

import adsk.core
import adsk.fusion
import traceback
import math
from . import fusionUtils


class GearParameters:
    ''' Gear parameters '''
    def __init__(self):
        self.rotor_thickness = 5
        self.housing_thickness = self.rotor_thickness * 2
        self.rotor_radius = 100
        self.num_pins = 10
        self.bore = 5
        self.num_gears = 1
        self.num_holes = 5
        self.drive_pin_diameter = 3
        self.hole_circle_diameter = 1
        self.eccentricity = 0.5

def run(context):
    default_name = 'Cycloidal Gear Generator'
    parameters = fusionUtils.Parameters()

    gear_params = GearParameters()

    parameters.addParameter('rotor_thickness', "mm", 'Rotor Thickness', gear_params.rotor_thickness)
    parameters.addParameter('housing_thickness', "mm", 'Housing Thickness', gear_params.housing_thickness)
    parameters.addParameter('rotor_radius', "mm", 'Rotor radius', gear_params.rotor_radius)
    parameters.addParameter('num_pins', "", 'Number of pins', gear_params.num_pins)
    parameters.addParameter('bore', "mm", 'Bore Diameter', gear_params.bore)
    parameters.addParameter('num_gears', "", 'Number of gears', gear_params.num_gears)
    parameters.addParameter('num_holes', "", 'Number of drive holes', gear_params.num_holes)
    parameters.addParameter('drive_pin_diameter', "mm", 'Diameter of drive pins', gear_params.drive_pin_diameter)
    parameters.addParameter('hole_circle_diameter', "mm", 'Diameter of (drive?) hole circle', gear_params.hole_circle_diameter)
    parameters.addParameter('eccentricity', "", 'Eccentricity', gear_params.eccentricity)

    created_object = CreatedObject()  # Create an instance of the designed class
    fusionUtils.run(parameters, default_name, created_object)


class CreatedObject:
    """ Part definitions """

    def __init__(self):
        self.parameters = {}

    def build(self, app, ui):
        """ Perform the features to create the component """

        newComp = fusionUtils.createNewComponent(app)
        if newComp is None:
            ui.messageBox('Failed to create new component', 'New Component Creation Failed')
            return

        units_mgr = app.activeProduct.unitsManager
        
        gear_params = GearParameters()
        
        #other constants based on the original inputs
        housing_cir = 2 * R * math.pi
        Rr = housing_cir / (4 * N)#roller radius
        E = eccentricityRatio * Rr#eccentricity
        maxDist = 0.25 * Rr #maximum allowed distance between points
        minDist = 0.5 * maxDist #the minimum allowed distance between points
        
        
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        root = design.rootComponent

        rotorOcc = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        rotor = rotorOcc.component
        rotor.name = 'rotor'

        sk = rotor.sketches.add(root.xYConstructionPlane)

        points = adsk.core.ObjectCollection.create()

        #ui.messageBox('Ratio will be ' + 1/N)

        (xs, ys) = getPoint(0, R, Rr, E, N)
        points.add(adsk.core.Point3D.create(xs,ys,0))

        et = 2 * math.pi / (N-1)
        (xe, ye) = getPoint(et, R, Rr, E, N)
        x = xs
        y = ys
        dist = 0
        ct = 0
        dt = math.pi / N
        numPoints = 0

        while ((math.sqrt((x-xe)**2 + (y-ye)**2) > maxDist or ct < et/2) and ct < et): #close enough to the end to call it, but over half way
        #while (ct < et/80): #close enough to the end to call it, but over half way
            (xt, yt) = getPoint(ct+dt, R, Rr, E, N)
            dist = getDist(x, y, xt, yt)

            ddt = dt/2
            lastTooBig = False
            lastTooSmall = False

            while (dist > maxDist or dist < minDist):
                if (dist > maxDist):
                    if (lastTooSmall):
                        ddt /= 2

                    lastTooSmall = False
                    lastTooBig = True

                    if (ddt > dt/2):
                        ddt = dt/2

                    dt -= ddt

                elif (dist < minDist):
                    if (lastTooBig):
                        ddt /= 2

                    lastTooSmall = True
                    lastTooBig = False
                    dt += ddt


                (xt, yt) = getPoint(ct+dt, R, Rr, E, N)
                dist = getDist(x, y, xt, yt)

            x = xt
            y = yt
            points.add(adsk.core.Point3D.create(x,y,0))
            numPoints += 1
            ct += dt

        points.add(adsk.core.Point3D.create(xe,ye,0))
        crv = sk.sketchCurves.sketchFittedSplines.add(points)

        lines = sk.sketchCurves.sketchLines
        line1 = lines.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), crv.startSketchPoint)
        line2 = lines.addByTwoPoints(line1.startSketchPoint, crv.endSketchPoint)

        prof = sk.profiles.item(0)
        distance = adsk.core.ValueInput.createByReal(rotorThickness)

        # Get extrude features
        extrudes = rotor.features.extrudeFeatures
        extrude1 = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

        # Get the extrusion body
        body1 = extrude1.bodies.item(0)
        body1.name = "rotor"

        inputEntites = adsk.core.ObjectCollection.create()
        inputEntites.add(body1)

        # Get Z axis for circular pattern
        zAxis = rotor.zConstructionAxis

        # Create the input for circular pattern
        circularFeats = rotor.features.circularPatternFeatures
        circularFeatInput = circularFeats.createInput(inputEntites, zAxis)

        # Set the quantity of the elements
        circularFeatInput.quantity = adsk.core.ValueInput.createByReal(N-1)

        # Set the angle of the circular pattern
        circularFeatInput.totalAngle = adsk.core.ValueInput.createByString('360 deg')

        # Set symmetry of the circular pattern
        circularFeatInput.isSymmetric = True

        # Create the circular pattern
        circularFeat = circularFeats.add(circularFeatInput)

        ToolBodies = adsk.core.ObjectCollection.create()
        for b in circularFeat.bodies:
            ToolBodies.add(b)

        combineInput = rotor.features.combineFeatures.createInput(body1, ToolBodies)
        combineInput.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        combineInput.isNewComponent = False

        rotor.features.combineFeatures.add(combineInput)

        #Offset the rotor to make the shaft rotat concentric with origin
        transform = rotorOcc.transform
        transform.translation = adsk.core.Vector3D.create(E, 0, 0)
        rotorOcc.transform = transform
        design.snapshots.add()

        housingOcc = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        housing = housingOcc.component
        housing.name = 'housing'

        #add a sketch so rotor clearance is obvious
        sketches = housing.sketches
        rotorClearanceSketch = sketches.add(root.xYConstructionPlane)
        sketchCircles = rotorClearanceSketch.sketchCurves.sketchCircles
        centerPoint = adsk.core.Point3D.create(0, 0, 0)
        sketchCircles.addByCenterRadius(centerPoint, R)

        #add rollers
        rollerSketch = sketches.add(root.xYConstructionPlane)
        sketchCircles = rollerSketch.sketchCurves.sketchCircles
        centerPoint = adsk.core.Point3D.create(R, 0, 0)
        sketchCircles.addByCenterRadius(centerPoint, Rr )

        rollerProfile = rollerSketch.profiles.item(0)
        distance = adsk.core.ValueInput.createByReal(housingThickness)
        rollerExtrudes = housing.features.extrudeFeatures.addSimple(rollerProfile, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

        # Get the extrusion body
        roller = rollerExtrudes.bodies.item(0)
        roller.name = "roller"

        inputEntites = adsk.core.ObjectCollection.create()
        inputEntites.add(roller)

        # Create the input for circular pattern
        circularFeats = housing.features.circularPatternFeatures
        zAxis = housing.zConstructionAxis
        circularFeatInput = circularFeats.createInput(inputEntites, zAxis)

        # Set the quantity of the elements
        circularFeatInput.quantity = adsk.core.ValueInput.createByReal(N)

        # Set the angle of the circular pattern
        circularFeatInput.totalAngle = adsk.core.ValueInput.createByString('360 deg')

        # Set symmetry of the circular pattern
        circularFeatInput.isSymmetric = True

        # Create the circular pattern
        circularFeat = circularFeats.add(circularFeatInput)


        # create center hole
        centerHoleSketch = sketches.add(root.xYConstructionPlane)
        sketchCircles = centerHoleSketch.sketchCurves.sketchCircles
        centerPoint = adsk.core.Point3D.create(E, 0, 0)
        sketchCircles.addByCenterRadius(centerPoint, bore/2)

        centerHoleProfile = centerHoleSketch.profiles.item(0)

        distance = adsk.core.ValueInput.createByReal(rotorThickness)
        centerExtrudes = housing.features.extrudeFeatures.addSimple(centerHoleProfile, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)


        #Create holes for pins

        if numHoles != 0:
            pinHoleSketch = sketches.add(root.xYConstructionPlane)
            sketchCircles = pinHoleSketch.sketchCurves.sketchCircles
            centerPoint = adsk.core.Point3D.create(E, holeCircleDiameter/2, 0)
            sketchCircles.addByCenterRadius(centerPoint, holePinDiameter/2 + E)

            pinHoleProfile = pinHoleSketch.profiles.item(0)

            distance = adsk.core.ValueInput.createByReal(rotorThickness)
            pinExtrudes = housing.features.extrudeFeatures.addSimple(pinHoleProfile, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)

            inputEntites = adsk.core.ObjectCollection.create()
            inputEntites.add(pinExtrudes)

            # Get Z axis for circular pattern
            zAxis = rotor.zConstructionAxis

            # Create the input for circular pattern
            circularFeats = rotor.features.circularPatternFeatures
            circularFeatInput = circularFeats.createInput(inputEntites, zAxis)

            # Set the quantity of the elements
            circularFeatInput.quantity = adsk.core.ValueInput.createByReal(numHoles)

            # Set the angle of the circular pattern
            circularFeatInput.totalAngle = adsk.core.ValueInput.createByString('360 deg')

            # Set symmetry of the circular pattern
            circularFeatInput.isSymmetric = True

            # Create the circular pattern
            circularFeat = circularFeats.add(circularFeatInput)


        # Create multiple gears

        body = body1
        
        # Check to see if the body is in the root component or another one.
        target = None
        if body.assemblyContext:
            # It's in another component.
            target = body.assemblyContext
        else:
            # It's in the root component.
            target = root

        # Get the xSize.
        xSize = body.boundingBox.maxPoint.x - body.boundingBox.minPoint.x            

        # Create several copies of the body.
        currentZ = 0
        for i in range(0,int(numGears)-1):
            # Create the copy.
            newBody = body.copyToComponent(target)
            
            # Increment the position.            
            currentZ +=  rotorThickness

            trans = adsk.core.Matrix3D.create()
            trans.translation = adsk.core.Vector3D.create(0, 0, currentZ)
            

            # Move the body using a move feature.
            bodyColl = adsk.core.ObjectCollection.create()
            bodyColl.add(newBody)
            moveInput = root.features.moveFeatures.createInput(bodyColl, trans)
            moveFeat = root.features.moveFeatures.add(moveInput)
            
            if (i%2 == 0):
                rotation = adsk.core.Matrix3D.create()
                rotation.setToRotation(units_mgr.convert(180, "deg", "rad"), root.yConstructionAxis.geometry.getData()[2], adsk.core.Point3D.create(0, 0, currentZ + rotorThickness/2))
                moveInput2 = root.features.moveFeatures.createInput(bodyColl, rotation)
                moveFeat = root.features.moveFeatures.add(moveInput2)


def getPoint(t, R, Rr, E, N):
    """ Get a point on a cycloid with the given parameters

        t: parameter
        R: major radius
        Rr: rolling radius
        E: eccentricity
        N: number of pins """
    psi = math.atan2(math.sin((1-N)*t), ((R/(E*N))-math.cos((1-N)*t)))
    x = (R*math.cos(t))-(Rr*math.cos(t+psi))-(E*math.cos(N*t))
    y = (-R*math.sin(t))+(Rr*math.sin(t+psi))+(E*math.sin(N*t))
    return (x,y)


def getDist(xa, ya, xb, yb):
    """ Get distance between two 2D points (xa,ya) and (xb,yb)"""
    return math.sqrt((xa-xb)**2 + (ya-yb)**2)
