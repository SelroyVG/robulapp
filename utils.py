import re
import difflib

def getXPathNumberOfLevels(xpath):
    return xpath.replace("//", "/").count("/")

# Calculates precision of the xpath expression
def CalculatePrecision(tree, xpath, correctNodes):
    nodeList = tree.xpath(xpath)
    countMatches = 0
    for correctNode in correctNodes:
        if(correctNode in nodeList):
            countMatches += 1
    if countMatches == len(correctNodes):
        return (1.0 * countMatches) / len(nodeList)
    else:
        return 0.0

def normalizeSpace(str):
    str = re.sub('\\t', ' ', str)
    str = re.sub('\\n', ' ', str)
    str = re.sub('\\xa0', ' ', str)
    return re.sub(' +', ' ', str)

# Decompiles xpath to a list of primitives
def decompileXpath(xpath):
    decompiled = list()
    while xpath is not "":
        if xpath.startswith("//"):
            decompiled.append("//")
            xpath = xpath[2:]
        elif xpath.startswith("/"):
            decompiled.append("/")
            xpath = xpath[1:]
        else:
            pos = xpath.find("/")
            if pos is not -1:
                decompiled.append(xpath[:pos])
                xpath = xpath[pos:]
            else:
                decompiled.append(xpath)
                return decompiled
    return decompiled


# Restores decompiled xpath
def compileXpath(decompiledList):
    compiled = ""
    for part in decompiledList:
        compiled = compiled + part
    return compiled

# Finds common substring sequences in a list of strings
def SequenceMatcher(listOfSequences):
    if  len(listOfSequences) <= 1:
        return listOfSequences

    matcher = difflib.SequenceMatcher(a=listOfSequences[0], b=listOfSequences[1])
    matches = matcher.get_matching_blocks()  # (0, len(matcher.a), 0, len(matcher.b))
    listMatches = list()
    for a, b, size in matches:
        if size > 1:
            listMatches.append(normalizeSpace(listOfSequences[0][a:a + size]))

    for sequence in listOfSequences:
        newMatches = list()
        for match in listMatches:
            matcher = difflib.SequenceMatcher(a=match, b=sequence)
            matches = matcher.get_matching_blocks()
            for a, b, size in matches:
                if (size > 0) and (match[a:a + size] is not " "):
                    newMatches.append(match[a:a + size])
        listMatches = newMatches
    for i in range(0, len(listMatches)):
        if listMatches[i].endswith(" "):
            listMatches[i] = listMatches[i][:-1]
        if listMatches[i].startswith(" "):
            listMatches[i] = listMatches[i][1:]

    filteredMatchesList = list()
    for match in listMatches:
        filteredMatch = re.match(r'([а-яА-Яa-zA-Z.\-])+', match)
        if filteredMatch is not None:
            filteredMatchesList.append(filteredMatch[0])
    return filteredMatchesList