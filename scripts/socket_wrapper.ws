@wrapMethod(W3GuiSocketsInventoryComponent)
function SetInventoryFlashObjectForItem(item : SItemUniqueId, out flashObject : CScriptedFlashObject) : void
{
    var socketItems : array<name>;
    var socketList : CScriptedFlashArray;
    var socketData : CScriptedFlashObject;
    var i : int;
    var usedSocketsCount : int;
    wrappedMethod(item, flashObject);
    _inv.GetItemEnhancementItems(item, socketItems);
    usedSocketsCount = _inv.GetItemEnhancementCount(item);
    socketList = flashObject.CreateFlashArray();
    for (i = 0; i < usedSocketsCount && i < socketItems.Size(); i += 1)
    {
        socketData = flashObject.CreateFlashObject();
        socketData.SetMemberFlashString("name", BilingualEnCnEnglishUpgradeName(socketItems[i], GetLocStringByKeyExt(_inv.GetItemLocalizedNameByName(socketItems[i]))));
        socketData.SetMemberFlashString("iconPath", _inv.GetItemIconPathByName(socketItems[i]));
        socketList.PushBackFlashObject(socketData);
    }
    flashObject.SetMemberFlashArray("socketsData", socketList);
}
