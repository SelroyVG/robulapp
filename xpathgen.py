import requests
from lxml import html
import re
import utils as Utils
import json
import argparse

attributeWhitelist = ["id", "class"]
attributeOrdinary = ["name", "title", "alt", "value"]
attributeBlacklist = ["href", "src", "onclick", "onload", "tabindex", "width", "height", "style", "size", "maxlength"]

MAX_XPATH_LEVELS = 4


def getFullPathToNode(node):
    currentNode = node
    fullPathList = []
    fullPathList.insert(0, currentNode)
    while currentNode is not None:
        currentNode = currentNode.xpath("..")[0]
        fullPathList.append(currentNode)
        if not currentNode.xpath(".."):
            break
    return fullPathList


def transfConvertStar(xpath, tagName):
    xpathList = list()
    if (xpath.startswith("//*")):
        xpathList.append(xpath.replace("//*", "//" + tagName))
    return xpathList


def transfAddAttribute(xpath, AttributeDictionary, tagName, useWhitelist):
    xpathList = list()
    index = 0
    currentTagXpath = ""
    if not AttributeDictionary:
        return xpathList
    if xpath.startswith("//*"):
        index = 3
        currentTagXpath = "*"
    else:
        index = len(tagName) + 2
        currentTagXpath = tagName

    if (len(xpath) == index) or (xpath[index] == "/"):
        for key, value in AttributeDictionary.items():
            if not (key in attributeBlacklist):
                if useWhitelist:
                    if not (key in attributeWhitelist):
                        continue
                else:
                    if key in attributeWhitelist:
                        continue
                attr = "[@" + key + "=\"" + value + "\"]"
                xpathList.append(xpath[:index] + attr + xpath[index:])
    return xpathList


def transfAddText(xpath, commonSequences):
    xpathList = list()
    for sequence in commonSequences:
        if len(sequence) < 30: # Ограничение на длину в 30 символов
            xpathList.append(xpath + "[contains(string(.), \"" + sequence + "\")]")
    return xpathList


def transfAddPosition(xpath, node):
    xpathList = list()
    index = 0
    currentTagXpath = ""
    if xpath.startswith("//body"):
        return xpathList

    if xpath.startswith("//*"):
        index = 3
        currentTagXpath = "*"
    else:
        index = len(node.tag) + 2
        currentTagXpath = node.tag

    if (len(xpath) == index) or (xpath[index] == "/") or (xpath[index + 1] == "@") or (xpath[index + 1] == "c"):
        position = 1
        parentNode = node.xpath("..")[0]
        siblingsList = parentNode.xpath("./" + node.tag)
        if len(siblingsList) > 1:
            for nodeSibling in siblingsList:
                if nodeSibling == node:
                    break
                position += 1
            attr = "[" + str(position) + "]"
            xpathList.append(xpath[:index] + attr + xpath[index:])
        else:
            return xpathList

    return xpathList


def transfAddLevel(xpath):
    xpathList = list()
    xpathList.append("//*" + xpath[1:])
    return xpathList


def transfRemoveLevel(xpath):
    xpathList = list()
    numberOfLevels = Utils.getXPathNumberOfLevels(xpath)
    if numberOfLevels > 2:
        for i in range(1, numberOfLevels - 2):
            decompiledXpath = Utils.decompileXpath(xpath)
            decompiledXpath[i * 2 + 2] = "//"
            del decompiledXpath[i * 2:i * 2 + 2]
            xpathList.append(Utils.compileXpath(decompiledXpath))

    return xpathList


# Смотрим все результаты и распихиваем по candidateXPathLocatorsList и robustXPathLocatorsList при надобности
def evaluateXPaths(DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList, trans):
    if len(trans) > 0:
        for xpath in trans:
            precision = Utils.CalculatePrecision(DOM, xpath, correctNodes)
            if precision == 1.0:
                duplicateXpath = False
                for robustXpath in robustXPathLocatorsList:
                    if robustXpath == xpath:
                        duplicateXpath = True
                if duplicateXpath == False:
                    robustXPathLocatorsList.append(xpath)
            elif precision > 0.0:
                candidateXPathLocatorsList.append(xpath)


def specialize(XpathCandidate, DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList,
               elementInfoFullPath, commonSequences=[]):
    currentElementPos = Utils.getXPathNumberOfLevels(XpathCandidate) - 1
    # Используем путь первого правильного узла, чтобы получить все остальные
    elementInfo = elementInfoFullPath[currentElementPos]
    resultXpathList = transfConvertStar(XpathCandidate, elementInfo.tag)
    evaluateXPaths(DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList, resultXpathList)

    useWhitelist = False
    if commonSequences and ('contains' not in XpathCandidate):
        resultXpathList = transfAddText(XpathCandidate, commonSequences)
        evaluateXPaths(DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList, resultXpathList)

    if not XpathCandidate.startswith("//*"):
        useWhitelist = True
        resultXpathList = transfAddAttribute(XpathCandidate, elementInfo.attrib, elementInfo.tag, useWhitelist)
        evaluateXPaths(DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList, resultXpathList)

        useWhitelist = False
        resultXpathList = transfAddAttribute(XpathCandidate, elementInfo.attrib, elementInfo.tag, useWhitelist)
        evaluateXPaths(DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList, resultXpathList)

        resultXpathList = transfAddPosition(XpathCandidate, elementInfo)
        evaluateXPaths(DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList, resultXpathList)

    levelsAbsoluteXPath = len(elementInfoFullPath)

    if ((Utils.getXPathNumberOfLevels(XpathCandidate) < (levelsAbsoluteXPath - 1)) and (
            Utils.getXPathNumberOfLevels(XpathCandidate) < MAX_XPATH_LEVELS)):
        resultXpathList = transfAddLevel(XpathCandidate)
        evaluateXPaths(DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList, resultXpathList)

    return candidateXPathLocatorsList, robustXPathLocatorsList


def finalSpecialize(DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList, elementInfoFullPath):
    for XpathCandidate in robustXPathLocatorsList:
        resultXpathList = transfRemoveLevel(XpathCandidate)
        evaluateXPaths(DOM, correctNodes, candidateXPathLocatorsList, robustXPathLocatorsList, resultXpathList)
    return candidateXPathLocatorsList, robustXPathLocatorsList


def RobulaPlusPlus(nodeList, DOM, commonSequences=[]):
    if not nodeList:
        return nodeList

    candidateXPathLocatorsList = list()
    robustXPathLocatorsList = list()
    fullPathElements = getFullPathToNode(nodeList[0])
    candidateXPathLocatorsList.append("//*")
    while (len(candidateXPathLocatorsList) > 0):
        candidateXPathLocatorsList, robustXPathLocatorsList = specialize(candidateXPathLocatorsList.pop(0), DOM,
                                                                         nodeList, candidateXPathLocatorsList,
                                                                         robustXPathLocatorsList, fullPathElements,
                                                                         commonSequences=commonSequences)
    candidateXPathLocatorsList, robustXPathLocatorsList = finalSpecialize(DOM, nodeList, candidateXPathLocatorsList,
                                                                          robustXPathLocatorsList, fullPathElements)
    return robustXPathLocatorsList


def sortByQuality(robustXpathList):
    weights = [0] * len(robustXpathList)

    for i in range(0, len(robustXpathList)):
        withoutNumbers = 5
        withoutStars = 3
        if re.search(r"\d+", robustXpathList[i]) is not None:
            withoutNumbers = 0
        if re.search(r"\*", robustXpathList[i]) is not None:
            withoutStars = 0
        weights[i] = weights[i] + MAX_XPATH_LEVELS + 1 - Utils.getXPathNumberOfLevels(robustXpathList[i]) + withoutNumbers + withoutStars

    # Сортирует список xpath выражений по качеству, в начале списка идут самые лучшие варианты
    # Правила:
    # - Меньше уровней -- лучше
    # - Нет цифр в аргументах -- лучше
    # - Если есть * -- хуже
    # - ??????
    return weights


def main(url, xpathList, importedTree=None):
    output = {}
    tree = None
    if importedTree is None:
        r = requests.get(url)
        rawString = r.content.decode("utf-8")
        rawString.replace("&nbsp;", " ")
        tree = html.fromstring(rawString)
    else:
        importedTree.replace("&nbsp;", " ")
        tree = html.fromstring("<html>" + importedTree + "</html>")
    nodeList = list()
    errors = {}
    for xpath in xpathList:
        try:
            nodes = tree.xpath(xpath)
        except Exception as e:
            errors["status"] = 400
            errors["title"] = "Bad request"
            errors["detail"] = "Error with recieved XPath occured: " + str(e)
        if not nodes:
            errors["status"] = 400
            errors["title"] = "Bad request"
            errors["detail"] = "Error: recieved xpath expressions are wrong"
        elif len(nodes) is 1:
            nodeList.append(nodes[0])
        else:
            errors["status"] = 400
            errors["title"] = "Bad request"
            errors["detail"] = "Error: recieved xpath expressions not unique"
    if nodeList is None:
        errors["status"] = 400
        errors["title"] = "Bad request"
        errors["detail"] = "Nodelist is empty"

    if errors:
        output["errors"] = errors
        return json.dumps(output)
		
    textStrings = list()
    for node in nodeList:
        textStrings.append(node.text_content())
    commonSequences = Utils.SequenceMatcher(textStrings)
    robustXpathList = RobulaPlusPlus(nodeList, tree, commonSequences=commonSequences)
    weights = sortByQuality(robustXpathList)
    results = list()
    for i in range(0, len(robustXpathList)):
        results.append({"value": robustXpathList[i], "ext_data": {"weight" : weights[i]}})
    output["results"] = results
    return json.dumps(output)


def exec(jsonStr):
    url = ""
    xpathList = []
    tree = None
    try:
        loadedJson = json.loads(jsonStr)
    except:
        output = {}
        errors = {}
        errors["status"] = 400
        errors["title"] = "Bad request"
        errors["detail"] = "JSON parsing error"
        output["errors"] = errors
        return json.dumps(output)

    for key, value in loadedJson.items():
        if key == "dom":
            tree = value
        if key == "url":
            url = value
        if key == "xpaths":
            xpathList = value
    return main(url, xpathList, importedTree=tree)

if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument('--data', type=str, help='JSON data')
    arguments, _ = args.parse_known_args()

    if arguments.data:
        exec(arguments.data)
    else:
        print("Can't find data argument, using debug values")
        url = "http://lavira.ru/s2/bluza-magnoliya-siniy"
        xpathList = ['//ul[@class="hmenu"]//a[@href="/prazdnik"]']
        tree = None
        print(main(url, xpathList, importedTree=tree))
