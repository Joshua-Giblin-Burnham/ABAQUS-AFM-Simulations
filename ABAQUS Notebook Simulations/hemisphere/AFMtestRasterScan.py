
# ----------------------------------------------Load Modules-----------------------------------------------------------
import numpy as np 
from abaqus import *
from abaqusConstants import *
from caeModules import *
from driverUtils import *
from part import *
from material import *
from section import *
from assembly import *
from interaction import *
from mesh import *
from visualization import *
import visualization
import odbAccess
from connectorBehavior import *
import cProfile, pstats, io
import regionToolset
#from abaqus import getInput
executeOnCaeStartup()

# ------------------------------------------------Set variables-------------------------------------------------------
with open('indentorType.txt', 'r') as f:
    indentorType = f.read()

elasticProperties =  np.loadtxt('elasticProperties.csv', delimiter=",")    
variables = np.loadtxt('variables.csv', delimiter=",")
baseDims  = np.loadtxt('baseDims.csv', delimiter=",")
tipDims   = np.loadtxt('tipDims.csv', delimiter=",")
rackPos   = np.loadtxt('rackPos.csv', delimiter=",")

timePeriod, timeInterval, binSize, indentionDepth, meshIndentor, meshSurface, rSurface = variables
rIndentor, theta, tip_length, r_int, z_int, r_top, z_top    = tipDims  

#  -------------------------------------------------Model-------------------------------------------------------------
modelName = 'AFMtestRasterScan'
model = mdb.Model(name=modelName)

# ------------------------------------------------Set Parts----------------------------------------------------------- 
# Create Surface part 
model.ConstrainedSketch(name = 'surface', sheetSize=1.0)   
model.sketches['surface'].ConstructionLine( point1=(0,rSurface), point2=(0,-rSurface) )
model.sketches['surface'].Line( point1=(0,0), point2=(0,rSurface) )
model.sketches['surface'].Line( point1=(0,0), point2=(rSurface,0) )
model.sketches['surface'].ArcByCenterEnds(center=(0,0),point1=(0,rSurface),point2=(rSurface,0),direction = CLOCKWISE)
model.Part(name='surface', dimensionality=THREE_D, type= DEFORMABLE_BODY)
model.parts['surface'].BaseSolidRevolve( angle=360.0, flipRevolveDirection=OFF, sketch= model.sketches['surface'] )

if indentorType == 'Capped':
    # Create Capped-Conical Indentor
    sketch = model.ConstrainedSketch(name = 'indentor', sheetSize=1.0)   
    model.sketches['indentor'].ConstructionLine(point1=(0,-rIndentor),point2=(0,z_top))
    model.sketches['indentor'].Line(point1=(r_int,z_int), point2=(r_top,z_top))
    model.sketches['indentor'].Line(point1=(0,-rIndentor), point2=(0,z_top))
    model.sketches['indentor'].Line(point1=(0,z_top), point2=(r_top,z_top))
    model.sketches['indentor'].ArcByCenterEnds(center=(0,0), point1=(r_int,z_int), point2=(0,-rIndentor),
                                               direction =CLOCKWISE)  
    model.Part(name='indentor', dimensionality=THREE_D, type= DISCRETE_RIGID_SURFACE)
    model.parts['indentor'].BaseShellRevolve(angle=360.0, flipRevolveDirection=OFF, sketch=model.sketches['indentor'])

else:
    # # Create Spherical Indentor part
    model.ConstrainedSketch(name = 'indentor', sheetSize=1.0)   
    model.sketches['indentor'].ConstructionLine(point1=(0,rIndentor),point2=(0,-rIndentor))
    model.sketches['indentor'].ArcByCenterEnds(center=(0,0),point1=(0,rIndentor),point2=(0,-rIndentor), 
                                               direction = CLOCKWISE)
    model.sketches['indentor'].Line(point1=(0,rIndentor),point2=(0,-rIndentor))
    model.Part(name='indentor', dimensionality=THREE_D, type=DISCRETE_RIGID_SURFACE)
    model.parts['indentor'].BaseShellRevolve( angle=360.0, flipRevolveDirection=OFF, sketch=model.sketches['indentor'])

# Create Base part
model.ConstrainedSketch(name = 'base', sheetSize=1.0) 
model.sketches['base'].rectangle(point1=(-baseDims[0]/2,-baseDims[1]/2), point2=(baseDims[0]/2,baseDims[1]/2))
model.Part(name='base', dimensionality=THREE_D, type= DEFORMABLE_BODY)
model.parts['base'].BaseSolidExtrude(sketch= model.sketches['base'], depth=baseDims[2])


# ----------------------------------------------Set Geometry----------------------------------------------------------
# Create geometric sets for faces and cells
model.parts['surface'].Set(faces= model.parts['surface'].faces.getSequenceFromMask(mask=('[#1]', ), ),
                           name='surface_faces')
model.parts['surface'].Set(cells= model.parts['surface'].cells.getSequenceFromMask(mask=('[#1]', ), ), 
                         name='surface_cells')
model.parts['surface'].Set(edges= model.parts['surface'].edges.getSequenceFromMask(mask=('[#2]', ), ), 
                         name='surface_base')
model.parts['base'].Set(faces = model.parts['base'].faces.getSequenceFromMask(mask=('[#20]', ), ), name='base_faces')
model.parts['base'].Set(cells = model.parts['base'].cells.getSequenceFromMask(mask=('[#1]' , ), ), name='base_cells')

if indentorType == 'Capped':
    # Spherically Capped
    model.parts['indentor'].Set(faces= model.parts['indentor'].faces.getSequenceFromMask(mask=('[#7]', ), ),
                                name='indentor_faces')
else: 
    # Spherical
    model.parts['indentor'].Set(faces= model.parts['indentor'].faces.getSequenceFromMask(mask=('[#1]', ), ),
                                name='indentor_faces')

# Create gemoetric surface for contact
model.parts['surface'].Surface(name='surface_surface', 
                               side1Faces = model.parts['surface'].faces.getSequenceFromMask(mask=('[#1]', ), ) )
model.parts['base'].Surface(name='base_surface', 
                            side1Faces = model.parts['base'].faces.getSequenceFromMask(mask=('[#20]', ), ) )

if indentorType == 'Capped':
    # Spherically Capped
    model.parts['indentor'].Surface(name='indentor_surface', 
                                    side1Faces = model.parts['indentor'].faces.getSequenceFromMask(mask=('[#7]', ), ))
else:
    # Spherical
    model.parts['indentor'].Surface(name='indentor_surface', 
                                    side1Faces = model.parts['indentor'].faces.getSequenceFromMask(mask=('[#1]', ), ))
    
# Create reference points
point = model.parts['surface'].ReferencePoint((0, 0, 0))
model.parts['surface'].Set(referencePoints=(model.parts['surface'].referencePoints[point.id],),
                           name='surface_centre')
point = model.parts['indentor'].ReferencePoint((0, 0, 0))
model.parts['indentor'].Set(referencePoints = (model.parts['indentor'].referencePoints[point.id],),
                            name = 'indentor_centre')
point = model.parts['base'].ReferencePoint((0, 0, 0))
model.parts['base'].Set(referencePoints = (model.parts['base'].referencePoints[point.id],), name= 'base_centre')


# -----------------------------------------------Set Properties-------------------------------------------------------
# Assign materials
elastic = (tuple(elasticProperties), )
viscoelastic = ((0.0403,0,0.649),(0.0458,0,1.695),)

# Surface material assignment
model.Material(name='surface_material')
model.materials['surface_material'].Elastic(table = elastic)
# model.materials['surface_material'].Viscoelastic(domain = FREQUENCY, frequency = PRONz, table = viscoelastic )
model.HomogeneousSolidSection(name='section', material='surface_material', thickness=None)
model.parts['surface'].SectionAssignment(region=model.parts['surface'].sets['surface_cells'],sectionName='section')

# Base material assignment
model.Material(name='base_material')
model.materials['base_material'].Elastic(table = ((1e15,0.4),))
model.HomogeneousSolidSection(name='base_section', material='base_material', thickness=None)
model.parts['base'].SectionAssignment(region = model.parts['base'].sets['base_cells'], sectionName='base_section')


# ----------------------------------------------Set Assembly----------------------------------------------------------
model.rootAssembly.Instance(name='surface', part = model.parts['surface'],dependent=ON)
model.rootAssembly.Instance(name='indentor', part = model.parts['indentor'], dependent=ON)
model.rootAssembly.Instance(name='base', part = model.parts['base'], dependent=ON)
model.rootAssembly.DatumCsysByDefault(CARTESIAN)
# Position base 
model.rootAssembly.rotate(instanceList = ('base',) , axisPoint=(0,0,0), axisDirection= (1,0,0), angle = 90 )


# ------------------------------------------------Set Steps-----------------------------------------------------------
model.StaticStep(name='Indentation', previous='Initial', description='', timePeriod=timePeriod, 
                 timeIncrementationMethod=AUTOMATIC, maxNumInc=int(1e5), initialInc=0.1, minInc=1e-20, maxInc=1)

model.steps['Indentation'].control.setValues(allowPropagation=OFF, resetDefaultValues=OFF, 
                                             timeIncrementation=(4.0, 8.0, 9.0, 16.0, 10.0, 4.0, 12.0, 25.0, 6.0, 3.0,
                                                                 50.0))
field = model.FieldOutputRequest('F-Output-1', createStepName='Indentation', variables=('RF', 'TF', 'U'), 
                                 timeInterval = timeInterval)


# ----------------------------------------------Set Interactions------------------------------------------------------
model.ContactProperty(name ='Contact Properties')
model.interactionProperties['Contact Properties'].TangentialBehavior(formulation =ROUGH)
model.interactionProperties['Contact Properties'].NormalBehavior(pressureOverclosure=HARD)

model.RigidBody(name = 'indentor_constraint', 
                bodyRegion = model.rootAssembly.instances['indentor'].sets['indentor_faces'],
                refPointRegion = model.rootAssembly.instances['indentor'].sets['indentor_centre'])

model.RigidBody(name = 'base_constraint', 
                bodyRegion = model.rootAssembly.instances['base'].sets['base_faces'],
                refPointRegion = model.rootAssembly.instances['base'].sets['base_centre'])

model.SurfaceToSurfaceContactStd(name = 'surface-indentor', 
                                 createStepName = 'Initial', 
                                 master = model.rootAssembly.instances['indentor'].surfaces['indentor_surface'], 
                                 slave  = model.rootAssembly.instances['surface'].surfaces['surface_surface'],
                                 interactionProperty = 'Contact Properties', 
                                 sliding = FINITE)

model.SurfaceToSurfaceContactStd(name = 'base-sphere', 
                                 createStepName = 'Initial', 
                                 master = model.rootAssembly.instances['base'].surfaces['base_surface'], 
                                 slave  = model.rootAssembly.instances['surface'].surfaces['surface_surface'],
                                 interactionProperty = 'Contact Properties', 
                                 sliding = FINITE)


# -----------------------------------------------Set Loads------------------------------------------------------------
# Create base boundary conditions
model.DisplacementBC(name = 'Base-BC', createStepName = 'Initial', 
                     region = model.rootAssembly.instances['base'].sets['base_faces'], 
                     u1 = SET, u2 = SET, u3 = SET, ur1 = SET, ur2 = SET, ur3 = SET)

# Create surface boundary conditions
model.DisplacementBC(name = 'Surface-BC', createStepName = 'Initial', 
                     region = model.rootAssembly.instances['surface'].sets['surface_base'], 
                     u1 = SET, u2 = SET, u3 = SET, ur1 = SET, ur2 = SET, ur3 = SET)

# Create indentor boundary conditions
model.DisplacementBC(name = 'Indentor-UC', createStepName = 'Indentation',                  
                     region = model.rootAssembly.instances['indentor'].sets['indentor_centre'], 
                     u1  = SET, u2  = -indentionDepth, u3  = SET,
                     ur1 = SET, ur2 = SET,             ur3 = SET)


# ------------------------------------------------Set Mesh------------------------------------------------------------
#Assign an element type to the part instance- seed and generate
model.rootAssembly.regenerate()

elemType1 = mesh.ElemType(elemCode=C3D20R, elemLibrary=STANDARD)
elemType2 = mesh.ElemType(elemCode=C3D15, elemLibrary=STANDARD)
elemType3 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD, secondOrderAccuracy=ON, distortionControl=DEFAULT)
cells     = model.parts['surface'].cells.getSequenceFromMask(mask=('[#1 ]', ), )

model.parts['surface'].seedPart(size=0.9, minSizeFactor=meshSurface)
model.parts['surface'].setMeshControls(regions=cells, elemShape=TET, technique=FREE)
model.parts['surface'].setElementType(regions=(cells,), elemTypes=(elemType1, elemType2, elemType3))
model.parts['surface'].generateMesh()


elemType1 = mesh.ElemType(elemCode=R3D4, elemLibrary=STANDARD)
elemType2 = mesh.ElemType(elemCode=R3D3, elemLibrary=STANDARD)
faces     = model.parts['indentor'].faces.getSequenceFromMask(mask=('[#1 ]', ),)

model.parts['indentor'].seedPart(size=0.5, minSizeFactor= meshIndentor)
model.parts['indentor'].setMeshControls(regions=faces, elemShape=TRI)
model.parts['indentor'].setElementType(regions=(faces,), elemTypes=(elemType1, elemType2))
model.parts['indentor'].generateMesh()


model.parts['base'].seedPart(size = 2 )
model.parts['base'].setElementType(model.rootAssembly.instances['base'].sets['base_faces'], 
                                      elemTypes = (mesh.ElemType(elemCode=QUAD, elemLibrary=STANDARD),))
model.parts['base'].setMeshControls(regions=model.rootAssembly.instances['base'].sets['base_faces'].vertices, 
                                       elemShape=TET,technique=FREE)
model.parts['base'].generateMesh()
    
# ----------------------------------------------Set Submission--------------------------------------------------------
for i in range(len(rackPos)):
    jobName = 'AFMtestRasterScan-Pos'+str(int(i))
    model.rootAssembly.translate(instanceList = ('indentor',), vector=(rackPos[i,0], rackPos[i,1]+rIndentor, 0))
    job = mdb.Job(name=jobName, model=modelName, description='AFM Sphere')
    job.writeInput()    
    model.rootAssembly.translate(instanceList = ('indentor',), vector=(-rackPos[i,0], -rackPos[i,1]-rIndentor, 0))
    
mdb.saveAs('AFMRaster.cae')
