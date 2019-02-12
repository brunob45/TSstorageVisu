from copy import deepcopy
from time import sleep
import json

f = open("./speeduino.ini", "r")

TYPES = ["scalar", "bits", "array"]
SIZES = ["U08", "S08", "U16", "S16"]

pageSize = []
pageNumber = None
pages = {}
defines = {}
data = {
    "define": defines,
    "pages": pages
}

scalartemplate = {
    "type": "scalar",
    "size": "U08",
    "offset": 0,
    "units": "%",
    "scale": 1.0,
    "translate": 0.0,
    "lo": 0.0,
    "hi": 1.0,
    "digits": 0
}

bitstemplate = {
    "type": "bits",
    "size": "U08",
    "offset": 0,
    "shape": [0,7],
    "values" : []
}

arraytemplate = {
    "type": "array",
    "size": "U08",
    "offset": 0,
    "shape": [8],
    "units": "%",
    "scale": 1.0,
    "translate": 0.0,
    "lo": 0.0,
    "hi": 1.0,
    "digits": 0
}


def getShape(shape):
    shape = shape.replace('[', '').replace(']', '').strip()
    if 'x' in shape:
        shape = shape.split('x')
        for index in range(len(shape)):
            shape[index] = int(shape[index].strip())
    elif ':' in shape:
        shape = shape.split(':')
        for index in range(len(shape)):
            shape[index] = int(shape[index].strip())
    else:
        shape = [int(shape)]
    return shape

def convert(values):
    # print(values)
    t = values[0]
    value = None
    if t == bitstemplate["type"]:
        value = deepcopy(bitstemplate)
        value["size"] = values[1]
        value["offset"] = int(values[2])
        value["shape"] = getShape(values[3])
        counter = 4
        for index in range(len(values)-4):
            value["values"].append(values[counter])
            counter += 1

    elif t == scalartemplate["type"]:
        value = deepcopy(scalartemplate)
        value["size"] = values[1]
        value["offset"] = int(values[2])
        value["units"] = values[3]
        value["scale"] = (values[4])
        value["translate"] = (values[5])
        if len(values) > 6:
            value["lo"] = (values[6])
        if len(values) > 7:
            value["hi"] = (values[7])
        if len(values) > 8:
            value["digits"] = (values[8])
    elif t == arraytemplate["type"]:
        value = deepcopy(arraytemplate)
        value["size"] = values[1]
        value["offset"] = int(values[2])
        value["shape"] = getShape(values[3])
        value["units"] = values[4]
        value["scale"] = (values[5])
        value["translate"] = (values[6])
        if len(values) > 7:
            value["lo"] = (values[7])
        if len(values) > 8:
            value["hi"] = (values[8])
        if len(values) > 9:
            value["digits"] = (values[9])
    else:
        print(values)
        print("error")

    return value

condition = None

for line in f:
    # Save comments
    comment = None
    if ';' in line:
        comment = line.split(';')[1]

    # Remove comments
    line = line.split(';')[0]

    # Checks if condition
    if "#if" in line:
        condition = line.replace("#if", '').strip()
    elif "#else" in line and condition:
        condition = "!(" + condition + ')'
    elif "#elif" in line and condition:
        newCond = line.replace("#elif", '').strip()
        condition = newCond + '&&!(' + condition + ')'
    elif "#endif" in line:
        condition = None

    # Find code that could be replaced by define
    for key, value in defines.items():
        while value in line and value.count(',') >= 4:
            line = line.replace(value, key)

    # If defining, add to list
    if "#define" in line and '=' in line:
        line = line.replace("#define", "").split('=')
        key = '$' + line[0].strip()
        value = line[1].strip()
        defines[key] = value

    # If defining page sizes, save value
    if "pageSize" in line:
        pageSize = line.split('=')[1].split(',')
        for index in range(len(pageSize)):
            pageSize[index] = int(pageSize[index].strip())

    # If at the end of pages, stop
    if "ConstantsExtensions" in line:
        break

    # Check if beginning new page
    if "page =" in line:
        number = line.split('=')[1].strip()
        pageNumber = int(number)
        pages[pageNumber] = {}

    # Put value in array
    elif (pageNumber) and ('=' in line) and (',' in line):
        line = line.split('=')
        name = line[0].strip().replace('-', '_')

        if condition:
            name += '&&'+condition

        while line[1].count('{') > 0:
            beg = line[1].find('{')
            end = line[1].find('}')
            if(beg < end):
                temp = line[1]
                line[1] = temp[0:beg] + temp[beg+1:end].replace(',', ';') + temp[end+1:len(temp)]
        while line[1].count('\"') >= 2:
            beg = line[1].find('\"')
            end = line[1].find('\"', beg+1)
            if(beg < end):
                temp = line[1]
                line[1] = temp[0:beg] + temp[beg+1:end].replace(',', ';') + temp[end+1:len(temp)]
        
        values = line[1].split(',')
        for index in range(len(values)):
            values[index] = values[index].strip()
        
        temp = convert(values)
        if temp:
            if comment:
                temp["comment"] = comment
            pages[pageNumber][name] = temp

for key, page in pages.items():
    nextOffset = 0.0
    for name, value in page.items():
        currentOffset = value["offset"]
        currentSize = 1
        if "bits" in value["type"]:
            currentSize = (value["shape"][1] - value["shape"][0]+1)/8
            currentOffset += value["shape"][0]/8
        elif "16" in value["size"]:
                currentSize = 2
        if "array" in value["type"]:
            for dim in value["shape"]:
                currentSize *= dim
    
        if currentOffset - nextOffset > 0.1:
            print("space between values", key, name, currentOffset - nextOffset)
            nextOffset = currentOffset + currentSize
        elif nextOffset - currentOffset > 0.1:
            if '&!' not in name:
                print("overlapping values", key, name, nextOffset - currentOffset)
                nextOffset = currentOffset + currentSize
        else:
            nextOffset = nextOffset + currentSize

    size = pageSize[key-1]
    if int(nextOffset) > size:
        print("page", key, "too big:", nextOffset, "vs", size)
    elif int(nextOffset) < size:
        space = size - nextOffset
        if space > 0.9:
            space = int(space)
            filler = deepcopy(arraytemplate)
            offset = size-space
            filler["offset"] = size-space
            filler["shape"] = [space]
            pages[key]["unused_"+str(key)+'_'+str(offset)] = filler
            nextOffset += space
        space = size-nextOffset
        if space > 0.1:
            filler = deepcopy(bitstemplate)
            filler["offset"] = size-1
            filler["shape"] = [8-int((space*8)), 7]
            pages[key]["unused_"+str(key)+'_'+str(size)] = filler
        print("filler added, page", key)


out = open("out.json", "w")
out.write(json.dumps(data, indent=4))
out.close()

out = open("configPages.h", "w")
out.write("#ifndef __CONFIG_PAGES_H__\n\
#define __CONFIG_PAGES_H__\n\n\
#include <Arduino.h>\n\n")

for pageNumber, page in pages.items():
    names = []
    out.write("struct config" + str(pageNumber) + "\n{\n")
    for key, value in page.items():
        name = key.split('&')[0]
        if name not in names:
            names.append(name)

            if value["size"] == "U08":
                out.write("  uint8_t ")
            elif value["size"] == "S08":
                out.write("  int8_t ")
            elif value["size"] == "U16":
                out.write("  uint16_t ")
            elif value["size"] == "S16":
                out.write("  int16_t ")

            out.write(name)

            if value["type"] == "bits":
                out.write(": " + str(value["shape"][1] - value["shape"][0]+1))
            elif value["type"] == "array":
                size = 1
                for i in value["shape"]:
                    size *= i
                out.write('[' + str(size) + ']')

            out.write(";\n")
    out.write("#if defined(CORE_AVR)\n\
};\n\
#else\n\
} __attribute__((__packed__)); //The 32 bi systems require all structs to be fully packed\n\
#endif\n\n")

out.write("#endif // __CONFIG_PAGES_H__")
