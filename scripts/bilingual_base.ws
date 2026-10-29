// English keeps the game's positional tokens. Chinese uses indexed tokens,
// so wrappedMethod consumes the original parameter arrays only once.
// Remastered 5.0 permits wrappers on these script-defined global functions.

function BilingualEnCnFillIndexedParams(resultString : string, intParamsArray : array<int>, floatParamsArray : array<float>, stringParamsArray : array<string>, optional addNbspTag : bool) : string
{
    var i : int;
    var prefix : string;

    if (StrFindFirst(resultString, "$BICN_") < 0)
        return resultString;

    prefix = "";
    if (addNbspTag)
        prefix = "&nbsp;";

    for (i = 0; i < intParamsArray.Size(); i += 1)
        resultString = StrReplaceAll(resultString, "$BICN_I" + IntToString(i) + "$", prefix + IntToString(intParamsArray[i]));
    for (i = 0; i < floatParamsArray.Size(); i += 1)
        resultString = StrReplaceAll(resultString, "$BICN_F" + IntToString(i) + "$", prefix + NoTrailZeros(floatParamsArray[i]));
    for (i = 0; i < stringParamsArray.Size(); i += 1)
        resultString = StrReplaceAll(resultString, "$BICN_S" + IntToString(i) + "$", prefix + stringParamsArray[i]);

    return resultString;
}

@wrapMethod
function GetLocStringByKeyExtWithParams(stringKey : string, optional intParamsArray : array<int>, optional floatParamsArray : array<float>, optional stringParamsArray : array<string>, optional addNbspTag : bool) : string
{
    var resultString : string;
    resultString = wrappedMethod(stringKey, intParamsArray, floatParamsArray, stringParamsArray, addNbspTag);
    return BilingualEnCnFillIndexedParams(resultString, intParamsArray, floatParamsArray, stringParamsArray, addNbspTag);
}

@wrapMethod
function GetLocStringByIdWithParams(stringId : int, optional intParamsArray : array<int>, optional floatParamsArray : array<float>, optional stringParamsArray : array<string>) : string
{
    var resultString : string;
    resultString = wrappedMethod(stringId, intParamsArray, floatParamsArray, stringParamsArray);
    return BilingualEnCnFillIndexedParams(resultString, intParamsArray, floatParamsArray, stringParamsArray);
}

