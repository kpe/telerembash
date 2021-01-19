
template variable expansion
===========================

variables starting with an underscore like in ${_SERVICE_NAME} are
expanded in python, e.g. provided in the string.Template.safe_expand() mapping argument.

All other variables get expanded in bash. To prevent variable expansion
all variable references without curly brackets will be escaped in python, i.e.

  $USER_NAME -> \$USER_NAME

so to keep a variable in script, reference it as $VAR_NAME, and to
expand it before it gets written reference it as ${VAR_NAME}.
