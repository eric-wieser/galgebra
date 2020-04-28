# derived from sympy's matexpr.py. Very incomplete

import itertools

from sympy.core import S
from sympy.core import Basic, Expr, Add, Mul, Symbol, Pow
from sympy.core.function import Function
from sympy.functions.elementary.exponential import exp
from sympy.core.operations import AssocOp
from sympy.core.decorators import _sympifyit, call_highest_priority
from sympy.core.compatibility import string_types, is_sequence, as_int, ordered
from sympy.sets.sets import Set, FiniteSet, Union
from sympy.sets.fancysets import Range
from sympy.printing.latex import LatexPrinter


def _grades_as_set(grades):
    if not isinstance(grades, Set):
        # Canonicalize grades here.  See also FunctionClass.
        if is_sequence(grades):
            grades = tuple(ordered(set(grades)))
        else:
            grades = (as_int(grades),)
        grades = FiniteSet(*grades)
    return grades


class GaExpr(Expr):
    """
    Base class for all multivector expressions, which overloads operators.

    Note that even the `+` operator must be overloaded, so that the result of
    ``(a + b)`` itself is a :class:`GaExpr`.
    """
    _iterable = False

    is_number = False
    is_symbol = False
    is_scalar = False

    def __neg__(self):
        ret = super().__neg__()
        return ret._exec_constructor_postprocessors(ret)

    # @_sympifyit('other', NotImplemented)
    # @call_highest_priority('__radd__')
    # def __add__(self, other):
    #     return GaAdd(self, other)

    # @_sympifyit('other', NotImplemented)
    # @call_highest_priority('__add__')
    # def __radd__(self, other):
    #     return GaAdd(other, self)

    # @_sympifyit('other', NotImplemented)
    # @call_highest_priority('__rsub__')
    # def __sub__(self, other):
    #     return GaAdd(self, -other)

    # @_sympifyit('other', NotImplemented)
    # @call_highest_priority('__sub__')
    # def __rsub__(self, other):
    #     return GaAdd(other, -self)

    # @_sympifyit('other', NotImplemented)
    # @call_highest_priority('__rmul__')
    # def __mul__(self, other):
    #     return GaMul(self, other)

    # @_sympifyit('other', NotImplemented)
    # @call_highest_priority('__mul__')
    # def __rmul__(self, other):
    #     return GaMul(other, self)

    @_sympifyit('other', NotImplemented)
    @call_highest_priority('__rxor__')
    def __xor__(self, other):
        return GaWedge(self, other)

    @_sympifyit('other', NotImplemented)
    @call_highest_priority('__xor__')
    def __rxor__(self, other):
        return GaWedge(other, self)

    @_sympifyit('other', NotImplemented)
    @call_highest_priority('__rxor__')
    def __or__(self, other):
        return GaDot(self, other)

    @_sympifyit('other', NotImplemented)
    @call_highest_priority('__xor__')
    def __ror__(self, other):
        return GaDot(other, self)

    def _eval_grades_present(self):
        return S.Naturals0

    def _eval_ga_grade_select(self, grades):
        return GaGradeSelect(self, grades, evaluate=False)


class GaScalar(GaExpr):
    def __new__(cls, x):
        if isinstance(x, GaExpr):
            return x
        return super().__new__(cls, x)

    def _eval_ga_grade_select(self, grades):
        if S(0) in grades:
            return self
        else:
            return GaAdd.identity

    def _eval_grades_present(self):
        if self.args[0] == S(0):
            return S.EmptySet
        else:
            return FiniteSet(0)


class GaAdd(GaExpr, Add):
    identity = GaScalar(S(0))

    def _eval_ga_grade_select(self, grades):
        return GaAdd(*(t._eval_ga_grade_select(grades) for t in self.args))

    def _eval_grades_present(self):
        return Union(*(t._eval_grades_present() for t in self.args))


class GaMul(GaExpr, Mul):
    identity = GaScalar(S(1))

    def _eval_grades_present(self):
        if len(self.args) != 2:
            raise NotImplementedError
        a = self.args[0]._eval_grades_present()
        b = self.args[1]._eval_grades_present()
        if a.is_iterable and b.is_iterable:
            return Union(*(
                Range(abs(ga - gb), ga + gb + 1, 2)
                for ga in a
                for gb in b
            ))
        raise NotImplementedError


class GaPow(GaExpr, Pow):
    pass


class GaExp(GaExpr, exp):
    pass


def _GaExpr_Mul_postprocessor(e: Mul):
    assert isinstance(e, Mul)
    return GaMul(*e.args)


def _GaExpr_Add_postprocessor(e: Add):
    assert isinstance(e, Add)
    return GaAdd(*e.args)


def _GaExpr_Pow_postprocessor(e: Pow):
    assert isinstance(e, Pow)
    return GaPow(*e.args)


def _GaExpr_Exp_postprocessor(e: exp):
    assert isinstance(e, exp)
    return GaExp(*e.args)


Basic._constructor_postprocessor_mapping[GaExpr] = {
    "Mul": [_GaExpr_Mul_postprocessor],
    "Add": [_GaExpr_Add_postprocessor],
    "Pow": [_GaExpr_Pow_postprocessor],
    "Exp": [_GaExpr_Exp_postprocessor],
}


class GaDot(GaExpr):
    # not associative, so require exactly two items
    def __new__(cls, a, b, **kwargs):
        return Basic.__new__(cls, a, b, **kwargs)

    def _eval_grades_present(self):
        a = self.args[0]._eval_grades_present()
        b = self.args[1]._eval_grades_present()
        if a.is_iterable and b.is_iterable:
            return FiniteSet(*(
                abs(ga - gb)
                for ga, gb in itertools.product(a, b)
            ))
        raise NotImplementedError


class GaWedge(GaExpr, AssocOp):
    identity = GaScalar(S(1))

    @classmethod
    def flatten(cls, args):
        c_part, nc_part, order_symbols = super(GaWedge, cls).flatten(args)
        seen = set()
        for a in nc_part:
            if a in seen:
                return [GaAdd.identity], [], None
            seen.add(a)
        return c_part, nc_part, order_symbols

    def _eval_grades_present(self):
        arg_grades = [
            arg._eval_grades_present()
            for arg in self.args
        ]
        if all(a.is_iterable for a in arg_grades):
            return FiniteSet(*(
                Add(*grades)
                for grades in itertools.product(*arg_grades)
            ))
        raise NotImplementedError


class GaGradeSelect(GaExpr, Function):
    nargs = 2

    def __new__(cls, obj, grades, **kwargs):
        grades = _grades_as_set(grades)
        return super().__new__(cls, obj, grades, **kwargs)

    @classmethod
    def eval(cls, obj, grades):
        # filter to the grades that are present
        present = obj._eval_grades_present()
        remaining = present & grades
        if remaining == S.EmptySet:
            return GaAdd.identity
        elif remaining == present:
            return obj
        else:
            return obj._eval_ga_grade_select(remaining)

    def _eval_grades_present(self):
        return self.args[0]._eval_grades_present() & self.args[1]


class GaGradesPresent(GaExpr, Function):
    nargs = 1

    @classmethod
    def eval(cls, obj):
        return obj._eval_grades_present()


class GaSymbol(GaExpr):
    is_symbol = True
    is_commutative = False

    def __new__(cls, name, grades=FiniteSet(1), **assumptions):
        if isinstance(name, string_types):
            name = Symbol(name)

        return Basic.__new__(cls, name, grades)

    @property
    def name(self):
        return self.args[0].name

    def _eval_grades_present(self):
        return self.args[1]


# now we monkey-patch the latex printer to know about our new types

def _patch(cls):
    def decorator(f):
        setattr(cls, f.__name__, f)
    return decorator


@_patch(LatexPrinter)
def _print_GaWedge(self, expr) -> str:
    tex = ""
    for i, term in enumerate(expr.args):
        if i == 0:
            pass
        else:
            tex += r" \wedge "
        term_tex = self._print(term)
        if self._needs_add_brackets(term):
            term_tex = r"\left(%s\right)" % term_tex
        tex += term_tex

    return tex


@_patch(LatexPrinter)
def _print_GaDot(self, expr: GaDot) -> str:
    tex = ""
    for i, term in enumerate(expr.args):
        if i == 0:
            pass
        else:
            tex += r" \cdot "
        term_tex = self._print(term)
        if self._needs_add_brackets(term):
            term_tex = r"\left(%s\right)" % term_tex
        tex += term_tex

    return tex


@_patch(LatexPrinter)
def _print_GaSymbol(self, expr: GaSymbol) -> str:
    return self._print_Symbol(expr, style=self._settings['ga_symbol_style'])


@_patch(LatexPrinter)
def _print_GaGradeSelect(self, expr: GaGradeSelect) -> str:
    obj, grades = expr.args
    return r"\left<{}\right>_{{{}}}".format(
        self._print(obj),
        ", ".join(self._print(g) for g in grades)
    )


LatexPrinter._default_settings['ga_symbol_style'] = 'plain'
# LatexPrinter._print_GaAdd = LatexPrinter._print_Add
# LatexPrinter._print_GaMul = LatexPrinter._print_Mul
