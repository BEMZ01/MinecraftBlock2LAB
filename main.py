import json
import math
import os
import random
import skimage
from PIL import Image
import shutil
import sys
import zipfile
import cv2
import numpy as np
import matplotlib.pyplot as plt


def GetVersion():
    versions = os.listdir(os.path.join(os.environ['APPDATA'], '.minecraft', 'versions'))
    print("AVALIABLE VERSIONS:")
    for version in [v for v in versions if v.isdigit() or '.' in v and not any(c.isalpha() for c in v)]:
        print(version)
    # if the flag -v is not set, then the latest version is returned
    if '-v' not in sys.argv:
        versions = [v for v in versions if v.isdigit() or '.' in v and not any(c.isalpha() for c in v)]
        # use the second number to get highest version
        highest_version = max(versions, key=lambda x: int(x.split('.')[1]))
        print("Detected highest version: " + highest_version + "\nUse the flag -v to override")
        return highest_version
    else:
        # if the flag -v is set, then the user is prompted to enter a version
        print("Enter the version you want to use:")
        version = input()
        if version in versions:
            return version
        else:
            print("Version not found")
            return False


def main():
    VERSION = GetVersion()
    if os.path.exists(os.path.join(os.getcwd(), f'builds\\{VERSION}')):
        shutil.rmtree(os.path.join(os.getcwd(), f'builds\\{VERSION}'))
    os.makedirs(os.path.join(os.getcwd(), f'builds\\{VERSION}'))

    # The path to the block textures changes in 1.13 and above
    if int(VERSION.split(".")[1]) > 13:
        walk_path = os.path.join(os.getcwd(), f'builds\\{VERSION}\\assets\\minecraft\\textures\\block')
    else:
        walk_path = os.path.join(os.getcwd(), f'builds\\{VERSION}\\assets\\minecraft\\textures\\blocks')

    # extract the assets from the jar file
    with zipfile.ZipFile(
            os.path.join(os.environ['APPDATA'], '.minecraft', 'versions', VERSION, VERSION + '.jar')) as zip_file:
        for file in zip_file.namelist():
            if file.startswith('assets/minecraft/textures/block/' if int(VERSION.split(".")[1]) > 13
                               else 'assets/minecraft/textures/blocks/') and file.endswith('.png'):
                zip_file.extract(file, os.getcwd() + f"/builds/{VERSION}")
                print("Extracted " + file)

    ################################################################
    # Sanitise the images (remove transparent images and duplicates)
    # Also check the name against a blacklist

    BLACKLIST = ["_bottom", "_side", "_particle", "_front", "_back", "_trapdoor", "_upper", "_lower"]
    for subdir, dirs, files in os.walk(os.path.join(os.getcwd(), walk_path)):
        for file in files:
            if file.endswith(".png"):
                if any(x in file for x in BLACKLIST):
                    try:
                        os.remove(os.path.join(subdir, file))
                    except FileNotFoundError:
                        pass
                    print("Removed " + file + " (Name)")
                    pass
                else:
                    try:
                        with Image.open(os.path.join(subdir, file)) as img:
                            for h in range(img.height-1):
                                complete = False
                                for w in range(img.width-1):
                                    color = img.getpixel((w, h))
                                    try:
                                        len(color)
                                    except TypeError:
                                        color = (color, color, color)
                                    if len(color) == 4:
                                        if color[3] < 100:
                                            complete = True
                                if complete:
                                    os.remove(os.path.join(subdir, file))
                                    if file.count("_") > 1:
                                        for file2 in files:
                                            if file2.startswith(file.split("_")[0]) and file2.endswith(".png"):
                                                fn = file.split("_")
                                                fn2 = file2.split("_")
                                                fn.pop()
                                                last = fn2.pop()
                                                fn = "_".join(fn)
                                                fn2 = "_".join(fn2)
                                                if fn == fn2 and file != file2 and last in BLACKLIST:
                                                    try:
                                                        os.remove(os.path.join(subdir, file2))
                                                    except FileNotFoundError:
                                                        pass
                                                    print("Removed " + file2 + " (Duplicate)")
                                        print("Removed " + file + " (Transparency)")
                    except FileNotFoundError:
                        pass
    colours = {}
    try:
        os.remove(f"build\\{VERSION}\\colors.txt")
    except FileNotFoundError:
        pass
    for subdir, dirs, files in os.walk(os.path.join(os.getcwd(), walk_path)):
        for file in files:
            if file.endswith(".png"):
                with Image.open(os.path.join(subdir, file)) as image:
                    colors = image.getcolors(image.size[0] * image.size[1])
                    # Sort the colors by the amount of pixels and get the most common color
                    colors.sort(key=lambda x: x[0], reverse=True)
                    # Get the color of the most common color
                    color = colors[0][1]
                    print("Color of " + file + ": " + str(color))
                    with open(f"builds\\{VERSION}\\colors.txt", "a") as f:
                        f.write(file + ":\t\t" + str(color) + "\n")
                    colours[file] = color
    with open(f'builds\\{VERSION}\\colors_rgb.json', "w") as f:
        json.dump(colours, f)

    ############################################################
    # generate the image of all the average colors of the blocks
    len_colors = len(colours)
    size = math.ceil(math.sqrt(len_colors))
    print("Creating image with size " + str(size) + "x" + str(size))
    image = Image.new("RGB", (size, size))
    for i in range(len_colors):
        rgb = colours[list(colours.keys())[i]]
        try:
            rgb = (rgb[0], rgb[1], rgb[2])
        except TypeError:
            rgb = (rgb, rgb, rgb)
        except IndexError:
            rgb = (rgb[0], rgb[0], rgb[0])
        image.putpixel((i % size, i // size), rgb)
    image.save(os.path.join(os.getcwd(), f"builds\\{VERSION}\\all_colors.png"))

    ##############################################################
    # create a 3d graph of all the blocks and their average colors

    image = cv2.imread(os.path.join(os.getcwd(), f"builds\\{VERSION}\\all_colors.png"))
    image_LAB = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)

    y, x, z = image_LAB.shape
    LAB_flat = np.reshape(image_LAB, [y * x, z])

    colors = np.reshape(image, [y * x, z]) / 255

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(xs=LAB_flat[:, 2], ys=LAB_flat[:, 1], zs=LAB_flat[:, 0], s=10, c=colors, lw=0)
    ax.set_xlabel('A')
    ax.set_ylabel('B')
    ax.set_zlabel('L')
    plt.savefig(os.path.join(os.getcwd(), f'builds\\{VERSION}\\all_colors_graph.png'))

    ###########################################################
    # Pack the data into json files for easy reference later on

    with open(f"builds\\{VERSION}\\colors_rgb.json", "r") as f:
        colours_rgb = json.load(f)
    colors_lab = {}
    for key, value in colours_rgb.items():
        try:
            value = (value[0], value[1], value[2])
        except TypeError:
            value = (value, value, value)
        except IndexError:
            value = (value[0], value[0], value[0])
        print(key, value)
        colors_lab[key] = list(skimage.color.rgb2lab(value))
        print(colors_lab[key])
    try:
        os.remove(f"builds\\{VERSION}\\colors_lab.json")
    except FileNotFoundError:
        pass
    with open(f"builds\\{VERSION}\\colors_lab.json", "w") as f:
        json.dump(colors_lab, f)

    ####################################################################################
    # TEST the data by converting a random color to lab and finding the closest MC Block
    # You can use this code as a reference for how to use the data in your own projects

    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    print("Using color: " + str(color))
    color = list(skimage.color.rgb2lab(color))
    with open(f"builds\\{VERSION}\\colors_lab.json", "r") as f:
        colors_lab = json.load(f)
    closest = None
    closest_distance = 10000000
    for key, value in colors_lab.items():
        distance = math.sqrt((color[0] - value[0]) ** 2 + (color[1] - value[1]) ** 2 + (color[2] - value[2]) ** 2)
        if distance < closest_distance:
            closest_distance = distance
            closest = key
    print("Closest color: " + closest)
    print("Distance: " + str(closest_distance))
    print("Color: " + str(colors_lab[closest]))
    print("Color (lab): " + str(skimage.color.lab2rgb(colors_lab[closest])))


if __name__ == "__main__":
    main()
