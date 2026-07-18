import ezdxf

path = r"data\DXF_TEST\SE-PI-PL-OC-330_B Canaletas y Ductos Para Cables Eléctricos - Planta.Rev B.dxf"


doc = ezdxf.readfile(path)

print("VERSION:")
print(doc.dxfversion)

print("\nLAYERS:")
for layer in doc.layers:
    print("-", layer.dxf.name)


print("\nFIRST ENTITIES:")

count = 0

for entity in doc.modelspace():

    print(
        entity.dxftype(),
        entity.dxf.handle,
        entity.dxf.layer
    )

    count += 1

    if count >= 20:
        break