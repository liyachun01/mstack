-- Native controls only. Never inspect credential/settings dialogs with this helper.
on run argv
 set actionName to item 1 of argv
 tell application "System Events" to tell process "Claude" to set rootNode to window 1
 set nodes to my collectNodes(rootNode, 0)
 tell application "System Events"
  if actionName is "inspect" then
   set report to ""
   repeat with n in nodes
    try
     set r to role of n
     set s to name of n
     if s is missing value then set s to ""
     if length of s > 140 then set s to "[long label omitted]"
     if s is not "" or r is "AXTextArea" or r is "AXTextField" then set report to report & r & " | " & s & linefeed
    end try
   end repeat
   return report
  else if actionName is "click" then
   repeat with n in nodes
    try
     if name of n is item 2 of argv then
      click n
      return "Clicked observed control"
     end if
    end try
   end repeat
   error "Observed control missing"
  else if actionName is "type-probe" then
   set inputNode to missing value
   repeat with n in nodes
    try
     if role of n is "AXTextArea" then
      set inputNode to contents of n
      exit repeat
     end if
    end try
   end repeat
   if inputNode is missing value then error "Chat input missing"
   tell process "Claude" to set frontmost to true
   set value of attribute "AXFocused" of inputNode to true
   keystroke "Connection test. Reply only MCP_STACK_DESKTOP_OK. Do not use tools or read files."
   key code 36
   return "Submitted synthetic probe"
  else
   error "Unsupported action"
  end if
 end tell
end run

on collectNodes(nodeRef, depth)
 if depth > 25 then return {}
 set resultNodes to {nodeRef}
 tell application "System Events" to set childrenNodes to UI elements of nodeRef
 repeat with childNode in childrenNodes
  set resultNodes to resultNodes & my collectNodes(childNode, depth + 1)
 end repeat
 return resultNodes
end collectNodes
