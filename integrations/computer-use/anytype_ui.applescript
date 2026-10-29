-- Existing macOS System Events only; no GUI automation dependency is installed.
-- Invoke through macctl with this existing source file as its translated argument.
on run argv
 tell application "Anytype" to activate
 delay 0.5
 tell application "System Events" to tell process "Anytype"
  set frontmost to true
  set priorManual to value of attribute "AXManualAccessibility"
  set value of attribute "AXManualAccessibility" to true
 end tell
 delay 0.3
 try
  set actionResult to my performAction(argv)
 on error messageText number errorNumber
  tell application "System Events" to tell process "Anytype" to set value of attribute "AXManualAccessibility" to priorManual
  error messageText number errorNumber
 end try
 tell application "System Events" to tell process "Anytype" to set value of attribute "AXManualAccessibility" to priorManual
 return actionResult
end run

on performAction(argv)
 set actionName to item 1 of argv
 tell application "System Events"
  tell process "Anytype"
   -- Some Electron builds expose AXWindow in children but omit AXWindows.
   try
    set targetWindow to window 1
   on error
    set targetWindow to first UI element whose role is "AXWindow"
   end try
   set nodes to my collectNodes(targetWindow, 0)
   if actionName is "headings" then
    set report to ""
    repeat with n in nodes
     try
      if role of n is "AXHeading" then set report to report & (name of n) & linefeed
     end try
    end repeat
    return report
   else if actionName is "inspect" then
    set report to ""
    repeat with n in nodes
     try
      set r to role of n
      set labelText to name of n
      if labelText is missing value then set labelText to ""
      if (count of labelText) > 40 then set labelText to "[long label omitted]"
      if labelText is not "" or r is "AXTextField" or r is "AXTextArea" or r is "AXCheckBox" or r is "AXRadioButton" then set report to report & r & " | " & labelText & linefeed
     end try
    end repeat
    return report
   else if actionName is "click" then
    set targetLabel to item 2 of argv
    repeat with n in nodes
     try
      if name of n is targetLabel then
       click n
       return "Clicked " & targetLabel
      end if
     end try
    end repeat
    error "Target not found or click failed"
   else if actionName is "save-new-key" then
    set createdHeading to false
    repeat with n in nodes
     try
      if role of n is "AXHeading" then
       set headingText to name of n
       if headingText is "API key successfully created" or headingText is "Clave de API creada correctamente" or headingText is "Clave API creada correctamente" then set createdHeading to true
      end if
     end try
    end repeat
    if not createdHeading then error "Not the newly created key dialog"
    repeat with n in nodes
     if role of n is "AXTextArea" then
      set secretText to value of n
      if (count of secretText) < 20 then error "New key missing"
      my saveSecret(secretText, item 2 of argv)
      return "New credential saved; value omitted"
     end if
    end repeat
    error "New key field not found"
   else if actionName is "controls" or actionName is "click-role" then
    set report to ""
    set controlIndex to 0
    repeat with n in nodes
     try
      set r to role of n
      if r is "AXCheckBox" or r is "AXPopUpButton" then
       set controlIndex to controlIndex + 1
       if actionName is "click-role" and controlIndex is (item 2 of argv as integer) then
        click n
        return "Clicked control " & controlIndex
       end if
       set report to report & controlIndex & " | " & r & " | " & (value of n) & linefeed
      end if
     end try
    end repeat
    return report
   else if actionName is "fields" then
    set report to ""
    set fieldIndex to 0
    repeat with n in nodes
     try
      if role of n is "AXTextField" or role of n is "AXTextArea" then
       set fieldIndex to fieldIndex + 1
       set placeholderText to ""
       try
        set placeholderText to value of attribute "AXPlaceholderValue" of n
       end try
       set report to report & fieldIndex & " | " & (role of n) & " | " & (description of n) & " | " & placeholderText & linefeed
      end if
     end try
    end repeat
    return report
   else if actionName is "fill" or actionName is "type" then
    set targetIndex to item 2 of argv as integer
    set fieldIndex to 0
    repeat with n in nodes
     try
      if role of n is "AXTextField" or role of n is "AXTextArea" then
       set fieldIndex to fieldIndex + 1
       if fieldIndex is targetIndex then
        if actionName is "type" then
         set frontmost to true
         click n
         keystroke "a" using command down
         keystroke item 3 of argv
         key code 48
        else
         set value of n to item 3 of argv
        end if
        return "Filled field " & targetIndex
       end if
      end if
     end try
    end repeat
    error "Field not found or fill failed"
   else
    error "Unsupported UI action"
   end if
  end tell
 end tell
end performAction

on collectNodes(nodeRef, depth)
 if depth > 30 then return {}
 set resultNodes to {nodeRef}
 tell application "System Events" to set childrenNodes to UI elements of nodeRef
 repeat with childNode in childrenNodes
  set resultNodes to resultNodes & my collectNodes(childNode, depth + 1)
 end repeat
 return resultNodes
end collectNodes

on saveSecret(secretText, targetPath)
 set outputFile to open for access (POSIX file targetPath) with write permission
 try
  set eof outputFile to 0
  write secretText to outputFile as «class utf8»
  close access outputFile
 on error
  close access outputFile
  error "Could not save credential"
 end try
end saveSecret
