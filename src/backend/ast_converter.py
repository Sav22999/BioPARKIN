import logging
import libsbml


# 18.07.12 td: some idiotic type mismatches for AST identifiers in different libsbml versions
if not type(libsbml.AST_PLUS) == type(1):
    libsbml.AST_PLUS = ord(libsbml.AST_PLUS)

if not type(libsbml.AST_MINUS) == type(1):
    libsbml.AST_MINUS = ord(libsbml.AST_MINUS)

if not type(libsbml.AST_TIMES) == type(1):
    libsbml.AST_TIMES = ord(libsbml.AST_TIMES)

if not type(libsbml.AST_DIVIDE) == type(1):
    libsbml.AST_DIVIDE = ord(libsbml.AST_DIVIDE)

if not type(libsbml.AST_POWER) == type(1):
    libsbml.AST_POWER = ord(libsbml.AST_POWER)



class AstConverter(object):
    """
    Takes a BaseAstConverterTemplate and delegates all "language"-specific calls to it,
    thereby converting a libsbml ASTNode tree into an adequate representation of the math therein (e.g.
    either valid FORTRAN syntax, or a PARKINcpp Expression tree, etc.)

    @since: 2010-12-21

    @param astConverterTemplate: This actually handles the conversion from ASTNode to the desired output.
    @type astConverterTemplate: A child of BaseAstConverterTemplate

    @param mainModel: The reference to the main model is needed to lookup some references within
        an ASTNode tree. Without the main model reference, most expressions can't be converted.
    @type mainModel: SbmlMainmodel

    @param idsToReplace: A dictionary with precomputed expressions that are inserted whenever
        an ASTNode leaf with an ID matching a dict key is encountered.
    @type idsToReplace: {}
    """

    __author__ = "Moritz Wade"
    __contact__ = "wade@zib.de"
    __copyright__ = "Zuse Institute Berlin 2010"

    def __init__(self, astConverterTemplate, mainModel=None,  idsToReplace=None):
        """
        A AstConverterTemplate needs to be provided. It defines the "language" to which to convert the libSBML
        ASTNode tree.

        The current SBML MainModel can be given as a reference. It is needed to resolve arbitrary functions that have
        been defined by the user.

        argsToReplace can be a dict with substitions for some libsbml.AST_NAME nodes' names.
        """
        if not astConverterTemplate:
            logging.debug("AstConverter.__init__(): No AstConverterTemplate given. Returning...")
            return

        astConverterTemplate.setAstConverter(self)  # set reference to self so that recursion can work

        self.astConverterTemplate = astConverterTemplate
        self.mainModel = mainModel
        self.idsToReplace = idsToReplace


    def handle(self, node):
        """
        Recursive function to evaluate the type of the given libSBML
        ASTNode and build up a math expression according to the given AstConverterTemplate.

        @param node: The ASTNode that should be converted.
        @type node: libsbml.ASTNode
        """
        if node is None:
            return None

        # handle node based on node type
        if node.getType() == libsbml.AST_CONSTANT_E:
            return self.astConverterTemplate.handleConstE(node)
        elif node.getType() == libsbml.AST_CONSTANT_PI:
            return self.astConverterTemplate.handleConstPi(node)
        elif node.getType() == libsbml.AST_CONSTANT_TRUE:
            return self.astConverterTemplate.handleConstTrue(node)
        elif node.getType() == libsbml.AST_CONSTANT_FALSE:
            return self.astConverterTemplate.handleConstFalse(node)

        if node.getType() == libsbml.AST_INTEGER:
            return self.astConverterTemplate.handleInt(node)
        elif node.isReal():
            return self.astConverterTemplate.handleReal(node)
        elif node.getType() == libsbml.AST_NAME_TIME:
            #logging.info("AstConverter.handle(): processing time variable as string: '%s'" % node.getName())
            return self.astConverterTemplate.handleOdeTime(node)
        elif node.getType() == libsbml.AST_NAME:
            if self.idsToReplace and node.getName() in self.idsToReplace.keys():
                return self.idsToReplace[node.getName()]
            else:
                return self.astConverterTemplate.handleString(node)

        elif node.getType() == libsbml.AST_PLUS:
            return self.astConverterTemplate.handlePlus(node)
        elif node.getType() == libsbml.AST_MINUS:
            return self.astConverterTemplate.handleMinus(node)
        elif node.getType() == libsbml.AST_DIVIDE:
            return self.astConverterTemplate.handleDivide(node)
        elif node.getType() == libsbml.AST_TIMES:
            return self.astConverterTemplate.handleTimes(node)
        elif node.getType() == libsbml.AST_POWER or node.getType() == libsbml.AST_FUNCTION_POWER:
            return self.astConverterTemplate.handlePower(node)
        elif node.getType() == libsbml.AST_FUNCTION_LN:
            return self.astConverterTemplate.handleLn(node)
        elif node.getType() == libsbml.AST_FUNCTION_LOG:
            return self.astConverterTemplate.handleLog(node)
        elif node.getType() == libsbml.AST_FUNCTION_EXP:
            return self.astConverterTemplate.handleExp(node)
        elif node.getType() == libsbml.AST_FUNCTION_ABS:
            return self.astConverterTemplate.handleAbs(node)
        elif node.getType() == libsbml.AST_FUNCTION_CEILING:
            return self.astConverterTemplate.handleCeiling(node)
        elif node.getType() == libsbml.AST_FUNCTION_FLOOR:
            return self.astConverterTemplate.handleFloor(node)
        elif node.getType() == libsbml.AST_FUNCTION_SIN:
            return self.astConverterTemplate.handleSin(node)
        elif node.getType() == libsbml.AST_FUNCTION_COS:
            return self.astConverterTemplate.handleCos(node)

        elif node.getType() == libsbml.AST_FUNCTION:
            # this has to be handled differently because in this case, we have
            # a function that is defined in the SBML itself
            #logging.info("AstConverter.handle(): Encountered a user function node in SBML model.")
            #logging.info("AstConverter.handle(): node.getName() = '%s'." % node.getName())
            if not self.mainModel:
                logging.debug("AstConverter.handle(): Can't handle node of type AST_FUNCTION without a reference to the main SBML model.")
                return None
            functionDefinition = self.mainModel.SbmlModel.Item.getFunctionDefinition(node.getName())

            mathNode = functionDefinition.getMath()

            numOfArguments = functionDefinition.getNumArguments()
            argsToReplace = {}
            for i in xrange(numOfArguments):
                arg = functionDefinition.getArgument(i)
                key = arg.getName()
                valueNode = node.getChild(i)
                value = self.handle(valueNode)
                #TODO: elif valueNode.isFunction():

                argsToReplace[key] = value
		#logging.info("AstConverter.handle(): Replace '%s': '%s'." % (key, value))
                mathNode.replaceArgument(key,valueNode)

            return self.handle(mathNode)

        elif node.getType() == libsbml.AST_LAMBDA:
            # the right child contains the body of the math expression
            #logging.info("AstConverter.handle(): Encountered a lambda function node in SBML model.")
            return self.handle(node.getRightChild())


        logging.error("AstConverter.handle(): Couldn't handle math node of type %s. The resulting expression will not be usable!" % node.getType())
        return "unsupported"
  
