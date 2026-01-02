var fp = Object.defineProperty;
var dp = (i, u, s) => (u in i ? fp(i, u, { enumerable: !0, configurable: !0, writable: !0, value: s }) : (i[u] = s));
var Ut = (i, u, s) => dp(i, typeof u != "symbol" ? u + "" : u, s);
(function () {
  const u = document.createElement("link").relList;
  if (u && u.supports && u.supports("modulepreload")) return;
  for (const f of document.querySelectorAll('link[rel="modulepreload"]')) c(f);
  new MutationObserver((f) => {
    for (const d of f)
      if (d.type === "childList")
        for (const h of d.addedNodes) h.tagName === "LINK" && h.rel === "modulepreload" && c(h);
  }).observe(document, { childList: !0, subtree: !0 });
  function s(f) {
    const d = {};
    return (
      f.integrity && (d.integrity = f.integrity),
      f.referrerPolicy && (d.referrerPolicy = f.referrerPolicy),
      f.crossOrigin === "use-credentials"
        ? (d.credentials = "include")
        : f.crossOrigin === "anonymous"
          ? (d.credentials = "omit")
          : (d.credentials = "same-origin"),
      d
    );
  }
  function c(f) {
    if (f.ep) return;
    f.ep = !0;
    const d = s(f);
    fetch(f.href, d);
  }
})();
function Ac(i) {
  return i && i.__esModule && Object.prototype.hasOwnProperty.call(i, "default") ? i.default : i;
}
var ns = { exports: {} },
  Fr = {},
  rs = { exports: {} },
  te = {};
/**
 * @license React
 * react.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var gc;
function pp() {
  if (gc) return te;
  gc = 1;
  var i = Symbol.for("react.element"),
    u = Symbol.for("react.portal"),
    s = Symbol.for("react.fragment"),
    c = Symbol.for("react.strict_mode"),
    f = Symbol.for("react.profiler"),
    d = Symbol.for("react.provider"),
    h = Symbol.for("react.context"),
    y = Symbol.for("react.forward_ref"),
    m = Symbol.for("react.suspense"),
    w = Symbol.for("react.memo"),
    S = Symbol.for("react.lazy"),
    R = Symbol.iterator;
  function j(x) {
    return x === null || typeof x != "object"
      ? null
      : ((x = (R && x[R]) || x["@@iterator"]), typeof x == "function" ? x : null);
  }
  var I = {
      isMounted: function () {
        return !1;
      },
      enqueueForceUpdate: function () {},
      enqueueReplaceState: function () {},
      enqueueSetState: function () {},
    },
    F = Object.assign,
    z = {};
  function D(x, L, b) {
    ((this.props = x), (this.context = L), (this.refs = z), (this.updater = b || I));
  }
  ((D.prototype.isReactComponent = {}),
    (D.prototype.setState = function (x, L) {
      if (typeof x != "object" && typeof x != "function" && x != null)
        throw Error(
          "setState(...): takes an object of state variables to update or a function which returns an object of state variables."
        );
      this.updater.enqueueSetState(this, x, L, "setState");
    }),
    (D.prototype.forceUpdate = function (x) {
      this.updater.enqueueForceUpdate(this, x, "forceUpdate");
    }));
  function $() {}
  $.prototype = D.prototype;
  function W(x, L, b) {
    ((this.props = x), (this.context = L), (this.refs = z), (this.updater = b || I));
  }
  var A = (W.prototype = new $());
  ((A.constructor = W), F(A, D.prototype), (A.isPureReactComponent = !0));
  var le = Array.isArray,
    ie = Object.prototype.hasOwnProperty,
    he = { current: null },
    xe = { key: !0, ref: !0, __self: !0, __source: !0 };
  function Re(x, L, b) {
    var re,
      ue = {},
      ae = null,
      ve = null;
    if (L != null)
      for (re in (L.ref !== void 0 && (ve = L.ref), L.key !== void 0 && (ae = "" + L.key), L))
        ie.call(L, re) && !xe.hasOwnProperty(re) && (ue[re] = L[re]);
    var de = arguments.length - 2;
    if (de === 1) ue.children = b;
    else if (1 < de) {
      for (var Se = Array(de), nt = 0; nt < de; nt++) Se[nt] = arguments[nt + 2];
      ue.children = Se;
    }
    if (x && x.defaultProps) for (re in ((de = x.defaultProps), de)) ue[re] === void 0 && (ue[re] = de[re]);
    return { $$typeof: i, type: x, key: ae, ref: ve, props: ue, _owner: he.current };
  }
  function Ie(x, L) {
    return { $$typeof: i, type: x.type, key: L, ref: x.ref, props: x.props, _owner: x._owner };
  }
  function ze(x) {
    return typeof x == "object" && x !== null && x.$$typeof === i;
  }
  function kt(x) {
    var L = { "=": "=0", ":": "=2" };
    return (
      "$" +
      x.replace(/[=:]/g, function (b) {
        return L[b];
      })
    );
  }
  var st = /\/+/g;
  function Fe(x, L) {
    return typeof x == "object" && x !== null && x.key != null ? kt("" + x.key) : L.toString(36);
  }
  function G(x, L, b, re, ue) {
    var ae = typeof x;
    (ae === "undefined" || ae === "boolean") && (x = null);
    var ve = !1;
    if (x === null) ve = !0;
    else
      switch (ae) {
        case "string":
        case "number":
          ve = !0;
          break;
        case "object":
          switch (x.$$typeof) {
            case i:
            case u:
              ve = !0;
          }
      }
    if (ve)
      return (
        (ve = x),
        (ue = ue(ve)),
        (x = re === "" ? "." + Fe(ve, 0) : re),
        le(ue)
          ? ((b = ""),
            x != null && (b = x.replace(st, "$&/") + "/"),
            G(ue, L, b, "", function (nt) {
              return nt;
            }))
          : ue != null &&
            (ze(ue) &&
              (ue = Ie(
                ue,
                b + (!ue.key || (ve && ve.key === ue.key) ? "" : ("" + ue.key).replace(st, "$&/") + "/") + x
              )),
            L.push(ue)),
        1
      );
    if (((ve = 0), (re = re === "" ? "." : re + ":"), le(x)))
      for (var de = 0; de < x.length; de++) {
        ae = x[de];
        var Se = re + Fe(ae, de);
        ve += G(ae, L, b, Se, ue);
      }
    else if (((Se = j(x)), typeof Se == "function"))
      for (x = Se.call(x), de = 0; !(ae = x.next()).done; )
        ((ae = ae.value), (Se = re + Fe(ae, de++)), (ve += G(ae, L, b, Se, ue)));
    else if (ae === "object")
      throw (
        (L = String(x)),
        Error(
          "Objects are not valid as a React child (found: " +
            (L === "[object Object]" ? "object with keys {" + Object.keys(x).join(", ") + "}" : L) +
            "). If you meant to render a collection of children, use an array instead."
        )
      );
    return ve;
  }
  function ee(x, L, b) {
    if (x == null) return x;
    var re = [],
      ue = 0;
    return (
      G(x, re, "", "", function (ae) {
        return L.call(b, ae, ue++);
      }),
      re
    );
  }
  function me(x) {
    if (x._status === -1) {
      var L = x._result;
      ((L = L()),
        L.then(
          function (b) {
            (x._status === 0 || x._status === -1) && ((x._status = 1), (x._result = b));
          },
          function (b) {
            (x._status === 0 || x._status === -1) && ((x._status = 2), (x._result = b));
          }
        ),
        x._status === -1 && ((x._status = 0), (x._result = L)));
    }
    if (x._status === 1) return x._result.default;
    throw x._result;
  }
  var oe = { current: null },
    U = { transition: null },
    Y = { ReactCurrentDispatcher: oe, ReactCurrentBatchConfig: U, ReactCurrentOwner: he };
  function H() {
    throw Error("act(...) is not supported in production builds of React.");
  }
  return (
    (te.Children = {
      map: ee,
      forEach: function (x, L, b) {
        ee(
          x,
          function () {
            L.apply(this, arguments);
          },
          b
        );
      },
      count: function (x) {
        var L = 0;
        return (
          ee(x, function () {
            L++;
          }),
          L
        );
      },
      toArray: function (x) {
        return (
          ee(x, function (L) {
            return L;
          }) || []
        );
      },
      only: function (x) {
        if (!ze(x)) throw Error("React.Children.only expected to receive a single React element child.");
        return x;
      },
    }),
    (te.Component = D),
    (te.Fragment = s),
    (te.Profiler = f),
    (te.PureComponent = W),
    (te.StrictMode = c),
    (te.Suspense = m),
    (te.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = Y),
    (te.act = H),
    (te.cloneElement = function (x, L, b) {
      if (x == null)
        throw Error("React.cloneElement(...): The argument must be a React element, but you passed " + x + ".");
      var re = F({}, x.props),
        ue = x.key,
        ae = x.ref,
        ve = x._owner;
      if (L != null) {
        if (
          (L.ref !== void 0 && ((ae = L.ref), (ve = he.current)),
          L.key !== void 0 && (ue = "" + L.key),
          x.type && x.type.defaultProps)
        )
          var de = x.type.defaultProps;
        for (Se in L)
          ie.call(L, Se) && !xe.hasOwnProperty(Se) && (re[Se] = L[Se] === void 0 && de !== void 0 ? de[Se] : L[Se]);
      }
      var Se = arguments.length - 2;
      if (Se === 1) re.children = b;
      else if (1 < Se) {
        de = Array(Se);
        for (var nt = 0; nt < Se; nt++) de[nt] = arguments[nt + 2];
        re.children = de;
      }
      return { $$typeof: i, type: x.type, key: ue, ref: ae, props: re, _owner: ve };
    }),
    (te.createContext = function (x) {
      return (
        (x = {
          $$typeof: h,
          _currentValue: x,
          _currentValue2: x,
          _threadCount: 0,
          Provider: null,
          Consumer: null,
          _defaultValue: null,
          _globalName: null,
        }),
        (x.Provider = { $$typeof: d, _context: x }),
        (x.Consumer = x)
      );
    }),
    (te.createElement = Re),
    (te.createFactory = function (x) {
      var L = Re.bind(null, x);
      return ((L.type = x), L);
    }),
    (te.createRef = function () {
      return { current: null };
    }),
    (te.forwardRef = function (x) {
      return { $$typeof: y, render: x };
    }),
    (te.isValidElement = ze),
    (te.lazy = function (x) {
      return { $$typeof: S, _payload: { _status: -1, _result: x }, _init: me };
    }),
    (te.memo = function (x, L) {
      return { $$typeof: w, type: x, compare: L === void 0 ? null : L };
    }),
    (te.startTransition = function (x) {
      var L = U.transition;
      U.transition = {};
      try {
        x();
      } finally {
        U.transition = L;
      }
    }),
    (te.unstable_act = H),
    (te.useCallback = function (x, L) {
      return oe.current.useCallback(x, L);
    }),
    (te.useContext = function (x) {
      return oe.current.useContext(x);
    }),
    (te.useDebugValue = function () {}),
    (te.useDeferredValue = function (x) {
      return oe.current.useDeferredValue(x);
    }),
    (te.useEffect = function (x, L) {
      return oe.current.useEffect(x, L);
    }),
    (te.useId = function () {
      return oe.current.useId();
    }),
    (te.useImperativeHandle = function (x, L, b) {
      return oe.current.useImperativeHandle(x, L, b);
    }),
    (te.useInsertionEffect = function (x, L) {
      return oe.current.useInsertionEffect(x, L);
    }),
    (te.useLayoutEffect = function (x, L) {
      return oe.current.useLayoutEffect(x, L);
    }),
    (te.useMemo = function (x, L) {
      return oe.current.useMemo(x, L);
    }),
    (te.useReducer = function (x, L, b) {
      return oe.current.useReducer(x, L, b);
    }),
    (te.useRef = function (x) {
      return oe.current.useRef(x);
    }),
    (te.useState = function (x) {
      return oe.current.useState(x);
    }),
    (te.useSyncExternalStore = function (x, L, b) {
      return oe.current.useSyncExternalStore(x, L, b);
    }),
    (te.useTransition = function () {
      return oe.current.useTransition();
    }),
    (te.version = "18.3.1"),
    te
  );
}
var _c;
function vs() {
  return (_c || ((_c = 1), (rs.exports = pp())), rs.exports);
}
/**
 * @license React
 * react-jsx-runtime.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var wc;
function hp() {
  if (wc) return Fr;
  wc = 1;
  var i = vs(),
    u = Symbol.for("react.element"),
    s = Symbol.for("react.fragment"),
    c = Object.prototype.hasOwnProperty,
    f = i.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner,
    d = { key: !0, ref: !0, __self: !0, __source: !0 };
  function h(y, m, w) {
    var S,
      R = {},
      j = null,
      I = null;
    (w !== void 0 && (j = "" + w), m.key !== void 0 && (j = "" + m.key), m.ref !== void 0 && (I = m.ref));
    for (S in m) c.call(m, S) && !d.hasOwnProperty(S) && (R[S] = m[S]);
    if (y && y.defaultProps) for (S in ((m = y.defaultProps), m)) R[S] === void 0 && (R[S] = m[S]);
    return { $$typeof: u, type: y, key: j, ref: I, props: R, _owner: f.current };
  }
  return ((Fr.Fragment = s), (Fr.jsx = h), (Fr.jsxs = h), Fr);
}
var xc;
function mp() {
  return (xc || ((xc = 1), (ns.exports = hp())), ns.exports);
}
var p = mp(),
  C = vs();
const vp = Ac(C);
var bl = {},
  ls = { exports: {} },
  tt = {},
  is = { exports: {} },
  os = {};
/**
 * @license React
 * scheduler.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var Sc;
function yp() {
  return (
    Sc ||
      ((Sc = 1),
      (function (i) {
        function u(U, Y) {
          var H = U.length;
          U.push(Y);
          e: for (; 0 < H; ) {
            var x = (H - 1) >>> 1,
              L = U[x];
            if (0 < f(L, Y)) ((U[x] = Y), (U[H] = L), (H = x));
            else break e;
          }
        }
        function s(U) {
          return U.length === 0 ? null : U[0];
        }
        function c(U) {
          if (U.length === 0) return null;
          var Y = U[0],
            H = U.pop();
          if (H !== Y) {
            U[0] = H;
            e: for (var x = 0, L = U.length, b = L >>> 1; x < b; ) {
              var re = 2 * (x + 1) - 1,
                ue = U[re],
                ae = re + 1,
                ve = U[ae];
              if (0 > f(ue, H))
                ae < L && 0 > f(ve, ue) ? ((U[x] = ve), (U[ae] = H), (x = ae)) : ((U[x] = ue), (U[re] = H), (x = re));
              else if (ae < L && 0 > f(ve, H)) ((U[x] = ve), (U[ae] = H), (x = ae));
              else break e;
            }
          }
          return Y;
        }
        function f(U, Y) {
          var H = U.sortIndex - Y.sortIndex;
          return H !== 0 ? H : U.id - Y.id;
        }
        if (typeof performance == "object" && typeof performance.now == "function") {
          var d = performance;
          i.unstable_now = function () {
            return d.now();
          };
        } else {
          var h = Date,
            y = h.now();
          i.unstable_now = function () {
            return h.now() - y;
          };
        }
        var m = [],
          w = [],
          S = 1,
          R = null,
          j = 3,
          I = !1,
          F = !1,
          z = !1,
          D = typeof setTimeout == "function" ? setTimeout : null,
          $ = typeof clearTimeout == "function" ? clearTimeout : null,
          W = typeof setImmediate < "u" ? setImmediate : null;
        typeof navigator < "u" &&
          navigator.scheduling !== void 0 &&
          navigator.scheduling.isInputPending !== void 0 &&
          navigator.scheduling.isInputPending.bind(navigator.scheduling);
        function A(U) {
          for (var Y = s(w); Y !== null; ) {
            if (Y.callback === null) c(w);
            else if (Y.startTime <= U) (c(w), (Y.sortIndex = Y.expirationTime), u(m, Y));
            else break;
            Y = s(w);
          }
        }
        function le(U) {
          if (((z = !1), A(U), !F))
            if (s(m) !== null) ((F = !0), me(ie));
            else {
              var Y = s(w);
              Y !== null && oe(le, Y.startTime - U);
            }
        }
        function ie(U, Y) {
          ((F = !1), z && ((z = !1), $(Re), (Re = -1)), (I = !0));
          var H = j;
          try {
            for (A(Y), R = s(m); R !== null && (!(R.expirationTime > Y) || (U && !kt())); ) {
              var x = R.callback;
              if (typeof x == "function") {
                ((R.callback = null), (j = R.priorityLevel));
                var L = x(R.expirationTime <= Y);
                ((Y = i.unstable_now()), typeof L == "function" ? (R.callback = L) : R === s(m) && c(m), A(Y));
              } else c(m);
              R = s(m);
            }
            if (R !== null) var b = !0;
            else {
              var re = s(w);
              (re !== null && oe(le, re.startTime - Y), (b = !1));
            }
            return b;
          } finally {
            ((R = null), (j = H), (I = !1));
          }
        }
        var he = !1,
          xe = null,
          Re = -1,
          Ie = 5,
          ze = -1;
        function kt() {
          return !(i.unstable_now() - ze < Ie);
        }
        function st() {
          if (xe !== null) {
            var U = i.unstable_now();
            ze = U;
            var Y = !0;
            try {
              Y = xe(!0, U);
            } finally {
              Y ? Fe() : ((he = !1), (xe = null));
            }
          } else he = !1;
        }
        var Fe;
        if (typeof W == "function")
          Fe = function () {
            W(st);
          };
        else if (typeof MessageChannel < "u") {
          var G = new MessageChannel(),
            ee = G.port2;
          ((G.port1.onmessage = st),
            (Fe = function () {
              ee.postMessage(null);
            }));
        } else
          Fe = function () {
            D(st, 0);
          };
        function me(U) {
          ((xe = U), he || ((he = !0), Fe()));
        }
        function oe(U, Y) {
          Re = D(function () {
            U(i.unstable_now());
          }, Y);
        }
        ((i.unstable_IdlePriority = 5),
          (i.unstable_ImmediatePriority = 1),
          (i.unstable_LowPriority = 4),
          (i.unstable_NormalPriority = 3),
          (i.unstable_Profiling = null),
          (i.unstable_UserBlockingPriority = 2),
          (i.unstable_cancelCallback = function (U) {
            U.callback = null;
          }),
          (i.unstable_continueExecution = function () {
            F || I || ((F = !0), me(ie));
          }),
          (i.unstable_forceFrameRate = function (U) {
            0 > U || 125 < U
              ? console.error(
                  "forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported"
                )
              : (Ie = 0 < U ? Math.floor(1e3 / U) : 5);
          }),
          (i.unstable_getCurrentPriorityLevel = function () {
            return j;
          }),
          (i.unstable_getFirstCallbackNode = function () {
            return s(m);
          }),
          (i.unstable_next = function (U) {
            switch (j) {
              case 1:
              case 2:
              case 3:
                var Y = 3;
                break;
              default:
                Y = j;
            }
            var H = j;
            j = Y;
            try {
              return U();
            } finally {
              j = H;
            }
          }),
          (i.unstable_pauseExecution = function () {}),
          (i.unstable_requestPaint = function () {}),
          (i.unstable_runWithPriority = function (U, Y) {
            switch (U) {
              case 1:
              case 2:
              case 3:
              case 4:
              case 5:
                break;
              default:
                U = 3;
            }
            var H = j;
            j = U;
            try {
              return Y();
            } finally {
              j = H;
            }
          }),
          (i.unstable_scheduleCallback = function (U, Y, H) {
            var x = i.unstable_now();
            switch (
              (typeof H == "object" && H !== null
                ? ((H = H.delay), (H = typeof H == "number" && 0 < H ? x + H : x))
                : (H = x),
              U)
            ) {
              case 1:
                var L = -1;
                break;
              case 2:
                L = 250;
                break;
              case 5:
                L = 1073741823;
                break;
              case 4:
                L = 1e4;
                break;
              default:
                L = 5e3;
            }
            return (
              (L = H + L),
              (U = { id: S++, callback: Y, priorityLevel: U, startTime: H, expirationTime: L, sortIndex: -1 }),
              H > x
                ? ((U.sortIndex = H),
                  u(w, U),
                  s(m) === null && U === s(w) && (z ? ($(Re), (Re = -1)) : (z = !0), oe(le, H - x)))
                : ((U.sortIndex = L), u(m, U), F || I || ((F = !0), me(ie))),
              U
            );
          }),
          (i.unstable_shouldYield = kt),
          (i.unstable_wrapCallback = function (U) {
            var Y = j;
            return function () {
              var H = j;
              j = Y;
              try {
                return U.apply(this, arguments);
              } finally {
                j = H;
              }
            };
          }));
      })(os)),
    os
  );
}
var kc;
function gp() {
  return (kc || ((kc = 1), (is.exports = yp())), is.exports);
}
/**
 * @license React
 * react-dom.production.min.js
 *
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var Ec;
function _p() {
  if (Ec) return tt;
  Ec = 1;
  var i = vs(),
    u = gp();
  function s(e) {
    for (var t = "https://reactjs.org/docs/error-decoder.html?invariant=" + e, n = 1; n < arguments.length; n++)
      t += "&args[]=" + encodeURIComponent(arguments[n]);
    return (
      "Minified React error #" +
      e +
      "; visit " +
      t +
      " for the full message or use the non-minified dev environment for full errors and additional helpful warnings."
    );
  }
  var c = new Set(),
    f = {};
  function d(e, t) {
    (h(e, t), h(e + "Capture", t));
  }
  function h(e, t) {
    for (f[e] = t, e = 0; e < t.length; e++) c.add(t[e]);
  }
  var y = !(typeof window > "u" || typeof window.document > "u" || typeof window.document.createElement > "u"),
    m = Object.prototype.hasOwnProperty,
    w =
      /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/,
    S = {},
    R = {};
  function j(e) {
    return m.call(R, e) ? !0 : m.call(S, e) ? !1 : w.test(e) ? (R[e] = !0) : ((S[e] = !0), !1);
  }
  function I(e, t, n, r) {
    if (n !== null && n.type === 0) return !1;
    switch (typeof t) {
      case "function":
      case "symbol":
        return !0;
      case "boolean":
        return r
          ? !1
          : n !== null
            ? !n.acceptsBooleans
            : ((e = e.toLowerCase().slice(0, 5)), e !== "data-" && e !== "aria-");
      default:
        return !1;
    }
  }
  function F(e, t, n, r) {
    if (t === null || typeof t > "u" || I(e, t, n, r)) return !0;
    if (r) return !1;
    if (n !== null)
      switch (n.type) {
        case 3:
          return !t;
        case 4:
          return t === !1;
        case 5:
          return isNaN(t);
        case 6:
          return isNaN(t) || 1 > t;
      }
    return !1;
  }
  function z(e, t, n, r, l, o, a) {
    ((this.acceptsBooleans = t === 2 || t === 3 || t === 4),
      (this.attributeName = r),
      (this.attributeNamespace = l),
      (this.mustUseProperty = n),
      (this.propertyName = e),
      (this.type = t),
      (this.sanitizeURL = o),
      (this.removeEmptyString = a));
  }
  var D = {};
  ("children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style"
    .split(" ")
    .forEach(function (e) {
      D[e] = new z(e, 0, !1, e, null, !1, !1);
    }),
    [
      ["acceptCharset", "accept-charset"],
      ["className", "class"],
      ["htmlFor", "for"],
      ["httpEquiv", "http-equiv"],
    ].forEach(function (e) {
      var t = e[0];
      D[t] = new z(t, 1, !1, e[1], null, !1, !1);
    }),
    ["contentEditable", "draggable", "spellCheck", "value"].forEach(function (e) {
      D[e] = new z(e, 2, !1, e.toLowerCase(), null, !1, !1);
    }),
    ["autoReverse", "externalResourcesRequired", "focusable", "preserveAlpha"].forEach(function (e) {
      D[e] = new z(e, 2, !1, e, null, !1, !1);
    }),
    "allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope"
      .split(" ")
      .forEach(function (e) {
        D[e] = new z(e, 3, !1, e.toLowerCase(), null, !1, !1);
      }),
    ["checked", "multiple", "muted", "selected"].forEach(function (e) {
      D[e] = new z(e, 3, !0, e, null, !1, !1);
    }),
    ["capture", "download"].forEach(function (e) {
      D[e] = new z(e, 4, !1, e, null, !1, !1);
    }),
    ["cols", "rows", "size", "span"].forEach(function (e) {
      D[e] = new z(e, 6, !1, e, null, !1, !1);
    }),
    ["rowSpan", "start"].forEach(function (e) {
      D[e] = new z(e, 5, !1, e.toLowerCase(), null, !1, !1);
    }));
  var $ = /[\-:]([a-z])/g;
  function W(e) {
    return e[1].toUpperCase();
  }
  ("accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height"
    .split(" ")
    .forEach(function (e) {
      var t = e.replace($, W);
      D[t] = new z(t, 1, !1, e, null, !1, !1);
    }),
    "xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function (e) {
      var t = e.replace($, W);
      D[t] = new z(t, 1, !1, e, "http://www.w3.org/1999/xlink", !1, !1);
    }),
    ["xml:base", "xml:lang", "xml:space"].forEach(function (e) {
      var t = e.replace($, W);
      D[t] = new z(t, 1, !1, e, "http://www.w3.org/XML/1998/namespace", !1, !1);
    }),
    ["tabIndex", "crossOrigin"].forEach(function (e) {
      D[e] = new z(e, 1, !1, e.toLowerCase(), null, !1, !1);
    }),
    (D.xlinkHref = new z("xlinkHref", 1, !1, "xlink:href", "http://www.w3.org/1999/xlink", !0, !1)),
    ["src", "href", "action", "formAction"].forEach(function (e) {
      D[e] = new z(e, 1, !1, e.toLowerCase(), null, !0, !0);
    }));
  function A(e, t, n, r) {
    var l = D.hasOwnProperty(t) ? D[t] : null;
    (l !== null
      ? l.type !== 0
      : r || !(2 < t.length) || (t[0] !== "o" && t[0] !== "O") || (t[1] !== "n" && t[1] !== "N")) &&
      (F(t, n, l, r) && (n = null),
      r || l === null
        ? j(t) && (n === null ? e.removeAttribute(t) : e.setAttribute(t, "" + n))
        : l.mustUseProperty
          ? (e[l.propertyName] = n === null ? (l.type === 3 ? !1 : "") : n)
          : ((t = l.attributeName),
            (r = l.attributeNamespace),
            n === null
              ? e.removeAttribute(t)
              : ((l = l.type),
                (n = l === 3 || (l === 4 && n === !0) ? "" : "" + n),
                r ? e.setAttributeNS(r, t, n) : e.setAttribute(t, n))));
  }
  var le = i.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,
    ie = Symbol.for("react.element"),
    he = Symbol.for("react.portal"),
    xe = Symbol.for("react.fragment"),
    Re = Symbol.for("react.strict_mode"),
    Ie = Symbol.for("react.profiler"),
    ze = Symbol.for("react.provider"),
    kt = Symbol.for("react.context"),
    st = Symbol.for("react.forward_ref"),
    Fe = Symbol.for("react.suspense"),
    G = Symbol.for("react.suspense_list"),
    ee = Symbol.for("react.memo"),
    me = Symbol.for("react.lazy"),
    oe = Symbol.for("react.offscreen"),
    U = Symbol.iterator;
  function Y(e) {
    return e === null || typeof e != "object"
      ? null
      : ((e = (U && e[U]) || e["@@iterator"]), typeof e == "function" ? e : null);
  }
  var H = Object.assign,
    x;
  function L(e) {
    if (x === void 0)
      try {
        throw Error();
      } catch (n) {
        var t = n.stack.trim().match(/\n( *(at )?)/);
        x = (t && t[1]) || "";
      }
    return (
      `
` +
      x +
      e
    );
  }
  var b = !1;
  function re(e, t) {
    if (!e || b) return "";
    b = !0;
    var n = Error.prepareStackTrace;
    Error.prepareStackTrace = void 0;
    try {
      if (t)
        if (
          ((t = function () {
            throw Error();
          }),
          Object.defineProperty(t.prototype, "props", {
            set: function () {
              throw Error();
            },
          }),
          typeof Reflect == "object" && Reflect.construct)
        ) {
          try {
            Reflect.construct(t, []);
          } catch (N) {
            var r = N;
          }
          Reflect.construct(e, [], t);
        } else {
          try {
            t.call();
          } catch (N) {
            r = N;
          }
          e.call(t.prototype);
        }
      else {
        try {
          throw Error();
        } catch (N) {
          r = N;
        }
        e();
      }
    } catch (N) {
      if (N && r && typeof N.stack == "string") {
        for (
          var l = N.stack.split(`
`),
            o = r.stack.split(`
`),
            a = l.length - 1,
            v = o.length - 1;
          1 <= a && 0 <= v && l[a] !== o[v];
        )
          v--;
        for (; 1 <= a && 0 <= v; a--, v--)
          if (l[a] !== o[v]) {
            if (a !== 1 || v !== 1)
              do
                if ((a--, v--, 0 > v || l[a] !== o[v])) {
                  var g =
                    `
` + l[a].replace(" at new ", " at ");
                  return (
                    e.displayName && g.includes("<anonymous>") && (g = g.replace("<anonymous>", e.displayName)),
                    g
                  );
                }
              while (1 <= a && 0 <= v);
            break;
          }
      }
    } finally {
      ((b = !1), (Error.prepareStackTrace = n));
    }
    return (e = e ? e.displayName || e.name : "") ? L(e) : "";
  }
  function ue(e) {
    switch (e.tag) {
      case 5:
        return L(e.type);
      case 16:
        return L("Lazy");
      case 13:
        return L("Suspense");
      case 19:
        return L("SuspenseList");
      case 0:
      case 2:
      case 15:
        return ((e = re(e.type, !1)), e);
      case 11:
        return ((e = re(e.type.render, !1)), e);
      case 1:
        return ((e = re(e.type, !0)), e);
      default:
        return "";
    }
  }
  function ae(e) {
    if (e == null) return null;
    if (typeof e == "function") return e.displayName || e.name || null;
    if (typeof e == "string") return e;
    switch (e) {
      case xe:
        return "Fragment";
      case he:
        return "Portal";
      case Ie:
        return "Profiler";
      case Re:
        return "StrictMode";
      case Fe:
        return "Suspense";
      case G:
        return "SuspenseList";
    }
    if (typeof e == "object")
      switch (e.$$typeof) {
        case kt:
          return (e.displayName || "Context") + ".Consumer";
        case ze:
          return (e._context.displayName || "Context") + ".Provider";
        case st:
          var t = e.render;
          return (
            (e = e.displayName),
            e || ((e = t.displayName || t.name || ""), (e = e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef")),
            e
          );
        case ee:
          return ((t = e.displayName || null), t !== null ? t : ae(e.type) || "Memo");
        case me:
          ((t = e._payload), (e = e._init));
          try {
            return ae(e(t));
          } catch {}
      }
    return null;
  }
  function ve(e) {
    var t = e.type;
    switch (e.tag) {
      case 24:
        return "Cache";
      case 9:
        return (t.displayName || "Context") + ".Consumer";
      case 10:
        return (t._context.displayName || "Context") + ".Provider";
      case 18:
        return "DehydratedFragment";
      case 11:
        return (
          (e = t.render),
          (e = e.displayName || e.name || ""),
          t.displayName || (e !== "" ? "ForwardRef(" + e + ")" : "ForwardRef")
        );
      case 7:
        return "Fragment";
      case 5:
        return t;
      case 4:
        return "Portal";
      case 3:
        return "Root";
      case 6:
        return "Text";
      case 16:
        return ae(t);
      case 8:
        return t === Re ? "StrictMode" : "Mode";
      case 22:
        return "Offscreen";
      case 12:
        return "Profiler";
      case 21:
        return "Scope";
      case 13:
        return "Suspense";
      case 19:
        return "SuspenseList";
      case 25:
        return "TracingMarker";
      case 1:
      case 0:
      case 17:
      case 2:
      case 14:
      case 15:
        if (typeof t == "function") return t.displayName || t.name || null;
        if (typeof t == "string") return t;
    }
    return null;
  }
  function de(e) {
    switch (typeof e) {
      case "boolean":
      case "number":
      case "string":
      case "undefined":
        return e;
      case "object":
        return e;
      default:
        return "";
    }
  }
  function Se(e) {
    var t = e.type;
    return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio");
  }
  function nt(e) {
    var t = Se(e) ? "checked" : "value",
      n = Object.getOwnPropertyDescriptor(e.constructor.prototype, t),
      r = "" + e[t];
    if (!e.hasOwnProperty(t) && typeof n < "u" && typeof n.get == "function" && typeof n.set == "function") {
      var l = n.get,
        o = n.set;
      return (
        Object.defineProperty(e, t, {
          configurable: !0,
          get: function () {
            return l.call(this);
          },
          set: function (a) {
            ((r = "" + a), o.call(this, a));
          },
        }),
        Object.defineProperty(e, t, { enumerable: n.enumerable }),
        {
          getValue: function () {
            return r;
          },
          setValue: function (a) {
            r = "" + a;
          },
          stopTracking: function () {
            ((e._valueTracker = null), delete e[t]);
          },
        }
      );
    }
  }
  function Wr(e) {
    e._valueTracker || (e._valueTracker = nt(e));
  }
  function Es(e) {
    if (!e) return !1;
    var t = e._valueTracker;
    if (!t) return !0;
    var n = t.getValue(),
      r = "";
    return (e && (r = Se(e) ? (e.checked ? "true" : "false") : e.value), (e = r), e !== n ? (t.setValue(e), !0) : !1);
  }
  function Vr(e) {
    if (((e = e || (typeof document < "u" ? document : void 0)), typeof e > "u")) return null;
    try {
      return e.activeElement || e.body;
    } catch {
      return e.body;
    }
  }
  function ui(e, t) {
    var n = t.checked;
    return H({}, t, {
      defaultChecked: void 0,
      defaultValue: void 0,
      value: void 0,
      checked: n ?? e._wrapperState.initialChecked,
    });
  }
  function Cs(e, t) {
    var n = t.defaultValue == null ? "" : t.defaultValue,
      r = t.checked != null ? t.checked : t.defaultChecked;
    ((n = de(t.value != null ? t.value : n)),
      (e._wrapperState = {
        initialChecked: r,
        initialValue: n,
        controlled: t.type === "checkbox" || t.type === "radio" ? t.checked != null : t.value != null,
      }));
  }
  function Ns(e, t) {
    ((t = t.checked), t != null && A(e, "checked", t, !1));
  }
  function ai(e, t) {
    Ns(e, t);
    var n = de(t.value),
      r = t.type;
    if (n != null)
      r === "number"
        ? ((n === 0 && e.value === "") || e.value != n) && (e.value = "" + n)
        : e.value !== "" + n && (e.value = "" + n);
    else if (r === "submit" || r === "reset") {
      e.removeAttribute("value");
      return;
    }
    (t.hasOwnProperty("value")
      ? ci(e, t.type, n)
      : t.hasOwnProperty("defaultValue") && ci(e, t.type, de(t.defaultValue)),
      t.checked == null && t.defaultChecked != null && (e.defaultChecked = !!t.defaultChecked));
  }
  function Rs(e, t, n) {
    if (t.hasOwnProperty("value") || t.hasOwnProperty("defaultValue")) {
      var r = t.type;
      if (!((r !== "submit" && r !== "reset") || (t.value !== void 0 && t.value !== null))) return;
      ((t = "" + e._wrapperState.initialValue), n || t === e.value || (e.value = t), (e.defaultValue = t));
    }
    ((n = e.name),
      n !== "" && (e.name = ""),
      (e.defaultChecked = !!e._wrapperState.initialChecked),
      n !== "" && (e.name = n));
  }
  function ci(e, t, n) {
    (t !== "number" || Vr(e.ownerDocument) !== e) &&
      (n == null
        ? (e.defaultValue = "" + e._wrapperState.initialValue)
        : e.defaultValue !== "" + n && (e.defaultValue = "" + n));
  }
  var Zn = Array.isArray;
  function Cn(e, t, n, r) {
    if (((e = e.options), t)) {
      t = {};
      for (var l = 0; l < n.length; l++) t["$" + n[l]] = !0;
      for (n = 0; n < e.length; n++)
        ((l = t.hasOwnProperty("$" + e[n].value)),
          e[n].selected !== l && (e[n].selected = l),
          l && r && (e[n].defaultSelected = !0));
    } else {
      for (n = "" + de(n), t = null, l = 0; l < e.length; l++) {
        if (e[l].value === n) {
          ((e[l].selected = !0), r && (e[l].defaultSelected = !0));
          return;
        }
        t !== null || e[l].disabled || (t = e[l]);
      }
      t !== null && (t.selected = !0);
    }
  }
  function fi(e, t) {
    if (t.dangerouslySetInnerHTML != null) throw Error(s(91));
    return H({}, t, { value: void 0, defaultValue: void 0, children: "" + e._wrapperState.initialValue });
  }
  function js(e, t) {
    var n = t.value;
    if (n == null) {
      if (((n = t.children), (t = t.defaultValue), n != null)) {
        if (t != null) throw Error(s(92));
        if (Zn(n)) {
          if (1 < n.length) throw Error(s(93));
          n = n[0];
        }
        t = n;
      }
      (t == null && (t = ""), (n = t));
    }
    e._wrapperState = { initialValue: de(n) };
  }
  function Ps(e, t) {
    var n = de(t.value),
      r = de(t.defaultValue);
    (n != null &&
      ((n = "" + n),
      n !== e.value && (e.value = n),
      t.defaultValue == null && e.defaultValue !== n && (e.defaultValue = n)),
      r != null && (e.defaultValue = "" + r));
  }
  function Ls(e) {
    var t = e.textContent;
    t === e._wrapperState.initialValue && t !== "" && t !== null && (e.value = t);
  }
  function Ts(e) {
    switch (e) {
      case "svg":
        return "http://www.w3.org/2000/svg";
      case "math":
        return "http://www.w3.org/1998/Math/MathML";
      default:
        return "http://www.w3.org/1999/xhtml";
    }
  }
  function di(e, t) {
    return e == null || e === "http://www.w3.org/1999/xhtml"
      ? Ts(t)
      : e === "http://www.w3.org/2000/svg" && t === "foreignObject"
        ? "http://www.w3.org/1999/xhtml"
        : e;
  }
  var Qr,
    Os = (function (e) {
      return typeof MSApp < "u" && MSApp.execUnsafeLocalFunction
        ? function (t, n, r, l) {
            MSApp.execUnsafeLocalFunction(function () {
              return e(t, n, r, l);
            });
          }
        : e;
    })(function (e, t) {
      if (e.namespaceURI !== "http://www.w3.org/2000/svg" || "innerHTML" in e) e.innerHTML = t;
      else {
        for (
          Qr = Qr || document.createElement("div"),
            Qr.innerHTML = "<svg>" + t.valueOf().toString() + "</svg>",
            t = Qr.firstChild;
          e.firstChild;
        )
          e.removeChild(e.firstChild);
        for (; t.firstChild; ) e.appendChild(t.firstChild);
      }
    });
  function bn(e, t) {
    if (t) {
      var n = e.firstChild;
      if (n && n === e.lastChild && n.nodeType === 3) {
        n.nodeValue = t;
        return;
      }
    }
    e.textContent = t;
  }
  var er = {
      animationIterationCount: !0,
      aspectRatio: !0,
      borderImageOutset: !0,
      borderImageSlice: !0,
      borderImageWidth: !0,
      boxFlex: !0,
      boxFlexGroup: !0,
      boxOrdinalGroup: !0,
      columnCount: !0,
      columns: !0,
      flex: !0,
      flexGrow: !0,
      flexPositive: !0,
      flexShrink: !0,
      flexNegative: !0,
      flexOrder: !0,
      gridArea: !0,
      gridRow: !0,
      gridRowEnd: !0,
      gridRowSpan: !0,
      gridRowStart: !0,
      gridColumn: !0,
      gridColumnEnd: !0,
      gridColumnSpan: !0,
      gridColumnStart: !0,
      fontWeight: !0,
      lineClamp: !0,
      lineHeight: !0,
      opacity: !0,
      order: !0,
      orphans: !0,
      tabSize: !0,
      widows: !0,
      zIndex: !0,
      zoom: !0,
      fillOpacity: !0,
      floodOpacity: !0,
      stopOpacity: !0,
      strokeDasharray: !0,
      strokeDashoffset: !0,
      strokeMiterlimit: !0,
      strokeOpacity: !0,
      strokeWidth: !0,
    },
    mf = ["Webkit", "ms", "Moz", "O"];
  Object.keys(er).forEach(function (e) {
    mf.forEach(function (t) {
      ((t = t + e.charAt(0).toUpperCase() + e.substring(1)), (er[t] = er[e]));
    });
  });
  function Ms(e, t, n) {
    return t == null || typeof t == "boolean" || t === ""
      ? ""
      : n || typeof t != "number" || t === 0 || (er.hasOwnProperty(e) && er[e])
        ? ("" + t).trim()
        : t + "px";
  }
  function Ds(e, t) {
    e = e.style;
    for (var n in t)
      if (t.hasOwnProperty(n)) {
        var r = n.indexOf("--") === 0,
          l = Ms(n, t[n], r);
        (n === "float" && (n = "cssFloat"), r ? e.setProperty(n, l) : (e[n] = l));
      }
  }
  var vf = H(
    { menuitem: !0 },
    {
      area: !0,
      base: !0,
      br: !0,
      col: !0,
      embed: !0,
      hr: !0,
      img: !0,
      input: !0,
      keygen: !0,
      link: !0,
      meta: !0,
      param: !0,
      source: !0,
      track: !0,
      wbr: !0,
    }
  );
  function pi(e, t) {
    if (t) {
      if (vf[e] && (t.children != null || t.dangerouslySetInnerHTML != null)) throw Error(s(137, e));
      if (t.dangerouslySetInnerHTML != null) {
        if (t.children != null) throw Error(s(60));
        if (typeof t.dangerouslySetInnerHTML != "object" || !("__html" in t.dangerouslySetInnerHTML))
          throw Error(s(61));
      }
      if (t.style != null && typeof t.style != "object") throw Error(s(62));
    }
  }
  function hi(e, t) {
    if (e.indexOf("-") === -1) return typeof t.is == "string";
    switch (e) {
      case "annotation-xml":
      case "color-profile":
      case "font-face":
      case "font-face-src":
      case "font-face-uri":
      case "font-face-format":
      case "font-face-name":
      case "missing-glyph":
        return !1;
      default:
        return !0;
    }
  }
  var mi = null;
  function vi(e) {
    return (
      (e = e.target || e.srcElement || window),
      e.correspondingUseElement && (e = e.correspondingUseElement),
      e.nodeType === 3 ? e.parentNode : e
    );
  }
  var yi = null,
    Nn = null,
    Rn = null;
  function Is(e) {
    if ((e = Sr(e))) {
      if (typeof yi != "function") throw Error(s(280));
      var t = e.stateNode;
      t && ((t = hl(t)), yi(e.stateNode, e.type, t));
    }
  }
  function zs(e) {
    Nn ? (Rn ? Rn.push(e) : (Rn = [e])) : (Nn = e);
  }
  function Fs() {
    if (Nn) {
      var e = Nn,
        t = Rn;
      if (((Rn = Nn = null), Is(e), t)) for (e = 0; e < t.length; e++) Is(t[e]);
    }
  }
  function As(e, t) {
    return e(t);
  }
  function Us() {}
  var gi = !1;
  function $s(e, t, n) {
    if (gi) return e(t, n);
    gi = !0;
    try {
      return As(e, t, n);
    } finally {
      ((gi = !1), (Nn !== null || Rn !== null) && (Us(), Fs()));
    }
  }
  function tr(e, t) {
    var n = e.stateNode;
    if (n === null) return null;
    var r = hl(n);
    if (r === null) return null;
    n = r[t];
    e: switch (t) {
      case "onClick":
      case "onClickCapture":
      case "onDoubleClick":
      case "onDoubleClickCapture":
      case "onMouseDown":
      case "onMouseDownCapture":
      case "onMouseMove":
      case "onMouseMoveCapture":
      case "onMouseUp":
      case "onMouseUpCapture":
      case "onMouseEnter":
        ((r = !r.disabled) ||
          ((e = e.type), (r = !(e === "button" || e === "input" || e === "select" || e === "textarea"))),
          (e = !r));
        break e;
      default:
        e = !1;
    }
    if (e) return null;
    if (n && typeof n != "function") throw Error(s(231, t, typeof n));
    return n;
  }
  var _i = !1;
  if (y)
    try {
      var nr = {};
      (Object.defineProperty(nr, "passive", {
        get: function () {
          _i = !0;
        },
      }),
        window.addEventListener("test", nr, nr),
        window.removeEventListener("test", nr, nr));
    } catch {
      _i = !1;
    }
  function yf(e, t, n, r, l, o, a, v, g) {
    var N = Array.prototype.slice.call(arguments, 3);
    try {
      t.apply(n, N);
    } catch (T) {
      this.onError(T);
    }
  }
  var rr = !1,
    Kr = null,
    qr = !1,
    wi = null,
    gf = {
      onError: function (e) {
        ((rr = !0), (Kr = e));
      },
    };
  function _f(e, t, n, r, l, o, a, v, g) {
    ((rr = !1), (Kr = null), yf.apply(gf, arguments));
  }
  function wf(e, t, n, r, l, o, a, v, g) {
    if ((_f.apply(this, arguments), rr)) {
      if (rr) {
        var N = Kr;
        ((rr = !1), (Kr = null));
      } else throw Error(s(198));
      qr || ((qr = !0), (wi = N));
    }
  }
  function dn(e) {
    var t = e,
      n = e;
    if (e.alternate) for (; t.return; ) t = t.return;
    else {
      e = t;
      do ((t = e), (t.flags & 4098) !== 0 && (n = t.return), (e = t.return));
      while (e);
    }
    return t.tag === 3 ? n : null;
  }
  function Bs(e) {
    if (e.tag === 13) {
      var t = e.memoizedState;
      if ((t === null && ((e = e.alternate), e !== null && (t = e.memoizedState)), t !== null)) return t.dehydrated;
    }
    return null;
  }
  function Hs(e) {
    if (dn(e) !== e) throw Error(s(188));
  }
  function xf(e) {
    var t = e.alternate;
    if (!t) {
      if (((t = dn(e)), t === null)) throw Error(s(188));
      return t !== e ? null : e;
    }
    for (var n = e, r = t; ; ) {
      var l = n.return;
      if (l === null) break;
      var o = l.alternate;
      if (o === null) {
        if (((r = l.return), r !== null)) {
          n = r;
          continue;
        }
        break;
      }
      if (l.child === o.child) {
        for (o = l.child; o; ) {
          if (o === n) return (Hs(l), e);
          if (o === r) return (Hs(l), t);
          o = o.sibling;
        }
        throw Error(s(188));
      }
      if (n.return !== r.return) ((n = l), (r = o));
      else {
        for (var a = !1, v = l.child; v; ) {
          if (v === n) {
            ((a = !0), (n = l), (r = o));
            break;
          }
          if (v === r) {
            ((a = !0), (r = l), (n = o));
            break;
          }
          v = v.sibling;
        }
        if (!a) {
          for (v = o.child; v; ) {
            if (v === n) {
              ((a = !0), (n = o), (r = l));
              break;
            }
            if (v === r) {
              ((a = !0), (r = o), (n = l));
              break;
            }
            v = v.sibling;
          }
          if (!a) throw Error(s(189));
        }
      }
      if (n.alternate !== r) throw Error(s(190));
    }
    if (n.tag !== 3) throw Error(s(188));
    return n.stateNode.current === n ? e : t;
  }
  function Ws(e) {
    return ((e = xf(e)), e !== null ? Vs(e) : null);
  }
  function Vs(e) {
    if (e.tag === 5 || e.tag === 6) return e;
    for (e = e.child; e !== null; ) {
      var t = Vs(e);
      if (t !== null) return t;
      e = e.sibling;
    }
    return null;
  }
  var Qs = u.unstable_scheduleCallback,
    Ks = u.unstable_cancelCallback,
    Sf = u.unstable_shouldYield,
    kf = u.unstable_requestPaint,
    Pe = u.unstable_now,
    Ef = u.unstable_getCurrentPriorityLevel,
    xi = u.unstable_ImmediatePriority,
    qs = u.unstable_UserBlockingPriority,
    Yr = u.unstable_NormalPriority,
    Cf = u.unstable_LowPriority,
    Ys = u.unstable_IdlePriority,
    Gr = null,
    Et = null;
  function Nf(e) {
    if (Et && typeof Et.onCommitFiberRoot == "function")
      try {
        Et.onCommitFiberRoot(Gr, e, void 0, (e.current.flags & 128) === 128);
      } catch {}
  }
  var vt = Math.clz32 ? Math.clz32 : Pf,
    Rf = Math.log,
    jf = Math.LN2;
  function Pf(e) {
    return ((e >>>= 0), e === 0 ? 32 : (31 - ((Rf(e) / jf) | 0)) | 0);
  }
  var Xr = 64,
    Jr = 4194304;
  function lr(e) {
    switch (e & -e) {
      case 1:
        return 1;
      case 2:
        return 2;
      case 4:
        return 4;
      case 8:
        return 8;
      case 16:
        return 16;
      case 32:
        return 32;
      case 64:
      case 128:
      case 256:
      case 512:
      case 1024:
      case 2048:
      case 4096:
      case 8192:
      case 16384:
      case 32768:
      case 65536:
      case 131072:
      case 262144:
      case 524288:
      case 1048576:
      case 2097152:
        return e & 4194240;
      case 4194304:
      case 8388608:
      case 16777216:
      case 33554432:
      case 67108864:
        return e & 130023424;
      case 134217728:
        return 134217728;
      case 268435456:
        return 268435456;
      case 536870912:
        return 536870912;
      case 1073741824:
        return 1073741824;
      default:
        return e;
    }
  }
  function Zr(e, t) {
    var n = e.pendingLanes;
    if (n === 0) return 0;
    var r = 0,
      l = e.suspendedLanes,
      o = e.pingedLanes,
      a = n & 268435455;
    if (a !== 0) {
      var v = a & ~l;
      v !== 0 ? (r = lr(v)) : ((o &= a), o !== 0 && (r = lr(o)));
    } else ((a = n & ~l), a !== 0 ? (r = lr(a)) : o !== 0 && (r = lr(o)));
    if (r === 0) return 0;
    if (
      t !== 0 &&
      t !== r &&
      (t & l) === 0 &&
      ((l = r & -r), (o = t & -t), l >= o || (l === 16 && (o & 4194240) !== 0))
    )
      return t;
    if (((r & 4) !== 0 && (r |= n & 16), (t = e.entangledLanes), t !== 0))
      for (e = e.entanglements, t &= r; 0 < t; ) ((n = 31 - vt(t)), (l = 1 << n), (r |= e[n]), (t &= ~l));
    return r;
  }
  function Lf(e, t) {
    switch (e) {
      case 1:
      case 2:
      case 4:
        return t + 250;
      case 8:
      case 16:
      case 32:
      case 64:
      case 128:
      case 256:
      case 512:
      case 1024:
      case 2048:
      case 4096:
      case 8192:
      case 16384:
      case 32768:
      case 65536:
      case 131072:
      case 262144:
      case 524288:
      case 1048576:
      case 2097152:
        return t + 5e3;
      case 4194304:
      case 8388608:
      case 16777216:
      case 33554432:
      case 67108864:
        return -1;
      case 134217728:
      case 268435456:
      case 536870912:
      case 1073741824:
        return -1;
      default:
        return -1;
    }
  }
  function Tf(e, t) {
    for (var n = e.suspendedLanes, r = e.pingedLanes, l = e.expirationTimes, o = e.pendingLanes; 0 < o; ) {
      var a = 31 - vt(o),
        v = 1 << a,
        g = l[a];
      (g === -1 ? ((v & n) === 0 || (v & r) !== 0) && (l[a] = Lf(v, t)) : g <= t && (e.expiredLanes |= v), (o &= ~v));
    }
  }
  function Si(e) {
    return ((e = e.pendingLanes & -1073741825), e !== 0 ? e : e & 1073741824 ? 1073741824 : 0);
  }
  function Gs() {
    var e = Xr;
    return ((Xr <<= 1), (Xr & 4194240) === 0 && (Xr = 64), e);
  }
  function ki(e) {
    for (var t = [], n = 0; 31 > n; n++) t.push(e);
    return t;
  }
  function ir(e, t, n) {
    ((e.pendingLanes |= t),
      t !== 536870912 && ((e.suspendedLanes = 0), (e.pingedLanes = 0)),
      (e = e.eventTimes),
      (t = 31 - vt(t)),
      (e[t] = n));
  }
  function Of(e, t) {
    var n = e.pendingLanes & ~t;
    ((e.pendingLanes = t),
      (e.suspendedLanes = 0),
      (e.pingedLanes = 0),
      (e.expiredLanes &= t),
      (e.mutableReadLanes &= t),
      (e.entangledLanes &= t),
      (t = e.entanglements));
    var r = e.eventTimes;
    for (e = e.expirationTimes; 0 < n; ) {
      var l = 31 - vt(n),
        o = 1 << l;
      ((t[l] = 0), (r[l] = -1), (e[l] = -1), (n &= ~o));
    }
  }
  function Ei(e, t) {
    var n = (e.entangledLanes |= t);
    for (e = e.entanglements; n; ) {
      var r = 31 - vt(n),
        l = 1 << r;
      ((l & t) | (e[r] & t) && (e[r] |= t), (n &= ~l));
    }
  }
  var pe = 0;
  function Xs(e) {
    return ((e &= -e), 1 < e ? (4 < e ? ((e & 268435455) !== 0 ? 16 : 536870912) : 4) : 1);
  }
  var Js,
    Ci,
    Zs,
    bs,
    eu,
    Ni = !1,
    br = [],
    Wt = null,
    Vt = null,
    Qt = null,
    or = new Map(),
    sr = new Map(),
    Kt = [],
    Mf =
      "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(
        " "
      );
  function tu(e, t) {
    switch (e) {
      case "focusin":
      case "focusout":
        Wt = null;
        break;
      case "dragenter":
      case "dragleave":
        Vt = null;
        break;
      case "mouseover":
      case "mouseout":
        Qt = null;
        break;
      case "pointerover":
      case "pointerout":
        or.delete(t.pointerId);
        break;
      case "gotpointercapture":
      case "lostpointercapture":
        sr.delete(t.pointerId);
    }
  }
  function ur(e, t, n, r, l, o) {
    return e === null || e.nativeEvent !== o
      ? ((e = { blockedOn: t, domEventName: n, eventSystemFlags: r, nativeEvent: o, targetContainers: [l] }),
        t !== null && ((t = Sr(t)), t !== null && Ci(t)),
        e)
      : ((e.eventSystemFlags |= r), (t = e.targetContainers), l !== null && t.indexOf(l) === -1 && t.push(l), e);
  }
  function Df(e, t, n, r, l) {
    switch (t) {
      case "focusin":
        return ((Wt = ur(Wt, e, t, n, r, l)), !0);
      case "dragenter":
        return ((Vt = ur(Vt, e, t, n, r, l)), !0);
      case "mouseover":
        return ((Qt = ur(Qt, e, t, n, r, l)), !0);
      case "pointerover":
        var o = l.pointerId;
        return (or.set(o, ur(or.get(o) || null, e, t, n, r, l)), !0);
      case "gotpointercapture":
        return ((o = l.pointerId), sr.set(o, ur(sr.get(o) || null, e, t, n, r, l)), !0);
    }
    return !1;
  }
  function nu(e) {
    var t = pn(e.target);
    if (t !== null) {
      var n = dn(t);
      if (n !== null) {
        if (((t = n.tag), t === 13)) {
          if (((t = Bs(n)), t !== null)) {
            ((e.blockedOn = t),
              eu(e.priority, function () {
                Zs(n);
              }));
            return;
          }
        } else if (t === 3 && n.stateNode.current.memoizedState.isDehydrated) {
          e.blockedOn = n.tag === 3 ? n.stateNode.containerInfo : null;
          return;
        }
      }
    }
    e.blockedOn = null;
  }
  function el(e) {
    if (e.blockedOn !== null) return !1;
    for (var t = e.targetContainers; 0 < t.length; ) {
      var n = ji(e.domEventName, e.eventSystemFlags, t[0], e.nativeEvent);
      if (n === null) {
        n = e.nativeEvent;
        var r = new n.constructor(n.type, n);
        ((mi = r), n.target.dispatchEvent(r), (mi = null));
      } else return ((t = Sr(n)), t !== null && Ci(t), (e.blockedOn = n), !1);
      t.shift();
    }
    return !0;
  }
  function ru(e, t, n) {
    el(e) && n.delete(t);
  }
  function If() {
    ((Ni = !1),
      Wt !== null && el(Wt) && (Wt = null),
      Vt !== null && el(Vt) && (Vt = null),
      Qt !== null && el(Qt) && (Qt = null),
      or.forEach(ru),
      sr.forEach(ru));
  }
  function ar(e, t) {
    e.blockedOn === t &&
      ((e.blockedOn = null), Ni || ((Ni = !0), u.unstable_scheduleCallback(u.unstable_NormalPriority, If)));
  }
  function cr(e) {
    function t(l) {
      return ar(l, e);
    }
    if (0 < br.length) {
      ar(br[0], e);
      for (var n = 1; n < br.length; n++) {
        var r = br[n];
        r.blockedOn === e && (r.blockedOn = null);
      }
    }
    for (
      Wt !== null && ar(Wt, e), Vt !== null && ar(Vt, e), Qt !== null && ar(Qt, e), or.forEach(t), sr.forEach(t), n = 0;
      n < Kt.length;
      n++
    )
      ((r = Kt[n]), r.blockedOn === e && (r.blockedOn = null));
    for (; 0 < Kt.length && ((n = Kt[0]), n.blockedOn === null); ) (nu(n), n.blockedOn === null && Kt.shift());
  }
  var jn = le.ReactCurrentBatchConfig,
    tl = !0;
  function zf(e, t, n, r) {
    var l = pe,
      o = jn.transition;
    jn.transition = null;
    try {
      ((pe = 1), Ri(e, t, n, r));
    } finally {
      ((pe = l), (jn.transition = o));
    }
  }
  function Ff(e, t, n, r) {
    var l = pe,
      o = jn.transition;
    jn.transition = null;
    try {
      ((pe = 4), Ri(e, t, n, r));
    } finally {
      ((pe = l), (jn.transition = o));
    }
  }
  function Ri(e, t, n, r) {
    if (tl) {
      var l = ji(e, t, n, r);
      if (l === null) (Qi(e, t, r, nl, n), tu(e, r));
      else if (Df(l, e, t, n, r)) r.stopPropagation();
      else if ((tu(e, r), t & 4 && -1 < Mf.indexOf(e))) {
        for (; l !== null; ) {
          var o = Sr(l);
          if ((o !== null && Js(o), (o = ji(e, t, n, r)), o === null && Qi(e, t, r, nl, n), o === l)) break;
          l = o;
        }
        l !== null && r.stopPropagation();
      } else Qi(e, t, r, null, n);
    }
  }
  var nl = null;
  function ji(e, t, n, r) {
    if (((nl = null), (e = vi(r)), (e = pn(e)), e !== null))
      if (((t = dn(e)), t === null)) e = null;
      else if (((n = t.tag), n === 13)) {
        if (((e = Bs(t)), e !== null)) return e;
        e = null;
      } else if (n === 3) {
        if (t.stateNode.current.memoizedState.isDehydrated) return t.tag === 3 ? t.stateNode.containerInfo : null;
        e = null;
      } else t !== e && (e = null);
    return ((nl = e), null);
  }
  function lu(e) {
    switch (e) {
      case "cancel":
      case "click":
      case "close":
      case "contextmenu":
      case "copy":
      case "cut":
      case "auxclick":
      case "dblclick":
      case "dragend":
      case "dragstart":
      case "drop":
      case "focusin":
      case "focusout":
      case "input":
      case "invalid":
      case "keydown":
      case "keypress":
      case "keyup":
      case "mousedown":
      case "mouseup":
      case "paste":
      case "pause":
      case "play":
      case "pointercancel":
      case "pointerdown":
      case "pointerup":
      case "ratechange":
      case "reset":
      case "resize":
      case "seeked":
      case "submit":
      case "touchcancel":
      case "touchend":
      case "touchstart":
      case "volumechange":
      case "change":
      case "selectionchange":
      case "textInput":
      case "compositionstart":
      case "compositionend":
      case "compositionupdate":
      case "beforeblur":
      case "afterblur":
      case "beforeinput":
      case "blur":
      case "fullscreenchange":
      case "focus":
      case "hashchange":
      case "popstate":
      case "select":
      case "selectstart":
        return 1;
      case "drag":
      case "dragenter":
      case "dragexit":
      case "dragleave":
      case "dragover":
      case "mousemove":
      case "mouseout":
      case "mouseover":
      case "pointermove":
      case "pointerout":
      case "pointerover":
      case "scroll":
      case "toggle":
      case "touchmove":
      case "wheel":
      case "mouseenter":
      case "mouseleave":
      case "pointerenter":
      case "pointerleave":
        return 4;
      case "message":
        switch (Ef()) {
          case xi:
            return 1;
          case qs:
            return 4;
          case Yr:
          case Cf:
            return 16;
          case Ys:
            return 536870912;
          default:
            return 16;
        }
      default:
        return 16;
    }
  }
  var qt = null,
    Pi = null,
    rl = null;
  function iu() {
    if (rl) return rl;
    var e,
      t = Pi,
      n = t.length,
      r,
      l = "value" in qt ? qt.value : qt.textContent,
      o = l.length;
    for (e = 0; e < n && t[e] === l[e]; e++);
    var a = n - e;
    for (r = 1; r <= a && t[n - r] === l[o - r]; r++);
    return (rl = l.slice(e, 1 < r ? 1 - r : void 0));
  }
  function ll(e) {
    var t = e.keyCode;
    return (
      "charCode" in e ? ((e = e.charCode), e === 0 && t === 13 && (e = 13)) : (e = t),
      e === 10 && (e = 13),
      32 <= e || e === 13 ? e : 0
    );
  }
  function il() {
    return !0;
  }
  function ou() {
    return !1;
  }
  function rt(e) {
    function t(n, r, l, o, a) {
      ((this._reactName = n),
        (this._targetInst = l),
        (this.type = r),
        (this.nativeEvent = o),
        (this.target = a),
        (this.currentTarget = null));
      for (var v in e) e.hasOwnProperty(v) && ((n = e[v]), (this[v] = n ? n(o) : o[v]));
      return (
        (this.isDefaultPrevented = (o.defaultPrevented != null ? o.defaultPrevented : o.returnValue === !1) ? il : ou),
        (this.isPropagationStopped = ou),
        this
      );
    }
    return (
      H(t.prototype, {
        preventDefault: function () {
          this.defaultPrevented = !0;
          var n = this.nativeEvent;
          n &&
            (n.preventDefault ? n.preventDefault() : typeof n.returnValue != "unknown" && (n.returnValue = !1),
            (this.isDefaultPrevented = il));
        },
        stopPropagation: function () {
          var n = this.nativeEvent;
          n &&
            (n.stopPropagation ? n.stopPropagation() : typeof n.cancelBubble != "unknown" && (n.cancelBubble = !0),
            (this.isPropagationStopped = il));
        },
        persist: function () {},
        isPersistent: il,
      }),
      t
    );
  }
  var Pn = {
      eventPhase: 0,
      bubbles: 0,
      cancelable: 0,
      timeStamp: function (e) {
        return e.timeStamp || Date.now();
      },
      defaultPrevented: 0,
      isTrusted: 0,
    },
    Li = rt(Pn),
    fr = H({}, Pn, { view: 0, detail: 0 }),
    Af = rt(fr),
    Ti,
    Oi,
    dr,
    ol = H({}, fr, {
      screenX: 0,
      screenY: 0,
      clientX: 0,
      clientY: 0,
      pageX: 0,
      pageY: 0,
      ctrlKey: 0,
      shiftKey: 0,
      altKey: 0,
      metaKey: 0,
      getModifierState: Di,
      button: 0,
      buttons: 0,
      relatedTarget: function (e) {
        return e.relatedTarget === void 0
          ? e.fromElement === e.srcElement
            ? e.toElement
            : e.fromElement
          : e.relatedTarget;
      },
      movementX: function (e) {
        return "movementX" in e
          ? e.movementX
          : (e !== dr &&
              (dr && e.type === "mousemove"
                ? ((Ti = e.screenX - dr.screenX), (Oi = e.screenY - dr.screenY))
                : (Oi = Ti = 0),
              (dr = e)),
            Ti);
      },
      movementY: function (e) {
        return "movementY" in e ? e.movementY : Oi;
      },
    }),
    su = rt(ol),
    Uf = H({}, ol, { dataTransfer: 0 }),
    $f = rt(Uf),
    Bf = H({}, fr, { relatedTarget: 0 }),
    Mi = rt(Bf),
    Hf = H({}, Pn, { animationName: 0, elapsedTime: 0, pseudoElement: 0 }),
    Wf = rt(Hf),
    Vf = H({}, Pn, {
      clipboardData: function (e) {
        return "clipboardData" in e ? e.clipboardData : window.clipboardData;
      },
    }),
    Qf = rt(Vf),
    Kf = H({}, Pn, { data: 0 }),
    uu = rt(Kf),
    qf = {
      Esc: "Escape",
      Spacebar: " ",
      Left: "ArrowLeft",
      Up: "ArrowUp",
      Right: "ArrowRight",
      Down: "ArrowDown",
      Del: "Delete",
      Win: "OS",
      Menu: "ContextMenu",
      Apps: "ContextMenu",
      Scroll: "ScrollLock",
      MozPrintableKey: "Unidentified",
    },
    Yf = {
      8: "Backspace",
      9: "Tab",
      12: "Clear",
      13: "Enter",
      16: "Shift",
      17: "Control",
      18: "Alt",
      19: "Pause",
      20: "CapsLock",
      27: "Escape",
      32: " ",
      33: "PageUp",
      34: "PageDown",
      35: "End",
      36: "Home",
      37: "ArrowLeft",
      38: "ArrowUp",
      39: "ArrowRight",
      40: "ArrowDown",
      45: "Insert",
      46: "Delete",
      112: "F1",
      113: "F2",
      114: "F3",
      115: "F4",
      116: "F5",
      117: "F6",
      118: "F7",
      119: "F8",
      120: "F9",
      121: "F10",
      122: "F11",
      123: "F12",
      144: "NumLock",
      145: "ScrollLock",
      224: "Meta",
    },
    Gf = { Alt: "altKey", Control: "ctrlKey", Meta: "metaKey", Shift: "shiftKey" };
  function Xf(e) {
    var t = this.nativeEvent;
    return t.getModifierState ? t.getModifierState(e) : (e = Gf[e]) ? !!t[e] : !1;
  }
  function Di() {
    return Xf;
  }
  var Jf = H({}, fr, {
      key: function (e) {
        if (e.key) {
          var t = qf[e.key] || e.key;
          if (t !== "Unidentified") return t;
        }
        return e.type === "keypress"
          ? ((e = ll(e)), e === 13 ? "Enter" : String.fromCharCode(e))
          : e.type === "keydown" || e.type === "keyup"
            ? Yf[e.keyCode] || "Unidentified"
            : "";
      },
      code: 0,
      location: 0,
      ctrlKey: 0,
      shiftKey: 0,
      altKey: 0,
      metaKey: 0,
      repeat: 0,
      locale: 0,
      getModifierState: Di,
      charCode: function (e) {
        return e.type === "keypress" ? ll(e) : 0;
      },
      keyCode: function (e) {
        return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
      },
      which: function (e) {
        return e.type === "keypress" ? ll(e) : e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
      },
    }),
    Zf = rt(Jf),
    bf = H({}, ol, {
      pointerId: 0,
      width: 0,
      height: 0,
      pressure: 0,
      tangentialPressure: 0,
      tiltX: 0,
      tiltY: 0,
      twist: 0,
      pointerType: 0,
      isPrimary: 0,
    }),
    au = rt(bf),
    ed = H({}, fr, {
      touches: 0,
      targetTouches: 0,
      changedTouches: 0,
      altKey: 0,
      metaKey: 0,
      ctrlKey: 0,
      shiftKey: 0,
      getModifierState: Di,
    }),
    td = rt(ed),
    nd = H({}, Pn, { propertyName: 0, elapsedTime: 0, pseudoElement: 0 }),
    rd = rt(nd),
    ld = H({}, ol, {
      deltaX: function (e) {
        return "deltaX" in e ? e.deltaX : "wheelDeltaX" in e ? -e.wheelDeltaX : 0;
      },
      deltaY: function (e) {
        return "deltaY" in e ? e.deltaY : "wheelDeltaY" in e ? -e.wheelDeltaY : "wheelDelta" in e ? -e.wheelDelta : 0;
      },
      deltaZ: 0,
      deltaMode: 0,
    }),
    id = rt(ld),
    od = [9, 13, 27, 32],
    Ii = y && "CompositionEvent" in window,
    pr = null;
  y && "documentMode" in document && (pr = document.documentMode);
  var sd = y && "TextEvent" in window && !pr,
    cu = y && (!Ii || (pr && 8 < pr && 11 >= pr)),
    fu = " ",
    du = !1;
  function pu(e, t) {
    switch (e) {
      case "keyup":
        return od.indexOf(t.keyCode) !== -1;
      case "keydown":
        return t.keyCode !== 229;
      case "keypress":
      case "mousedown":
      case "focusout":
        return !0;
      default:
        return !1;
    }
  }
  function hu(e) {
    return ((e = e.detail), typeof e == "object" && "data" in e ? e.data : null);
  }
  var Ln = !1;
  function ud(e, t) {
    switch (e) {
      case "compositionend":
        return hu(t);
      case "keypress":
        return t.which !== 32 ? null : ((du = !0), fu);
      case "textInput":
        return ((e = t.data), e === fu && du ? null : e);
      default:
        return null;
    }
  }
  function ad(e, t) {
    if (Ln)
      return e === "compositionend" || (!Ii && pu(e, t)) ? ((e = iu()), (rl = Pi = qt = null), (Ln = !1), e) : null;
    switch (e) {
      case "paste":
        return null;
      case "keypress":
        if (!(t.ctrlKey || t.altKey || t.metaKey) || (t.ctrlKey && t.altKey)) {
          if (t.char && 1 < t.char.length) return t.char;
          if (t.which) return String.fromCharCode(t.which);
        }
        return null;
      case "compositionend":
        return cu && t.locale !== "ko" ? null : t.data;
      default:
        return null;
    }
  }
  var cd = {
    color: !0,
    date: !0,
    datetime: !0,
    "datetime-local": !0,
    email: !0,
    month: !0,
    number: !0,
    password: !0,
    range: !0,
    search: !0,
    tel: !0,
    text: !0,
    time: !0,
    url: !0,
    week: !0,
  };
  function mu(e) {
    var t = e && e.nodeName && e.nodeName.toLowerCase();
    return t === "input" ? !!cd[e.type] : t === "textarea";
  }
  function vu(e, t, n, r) {
    (zs(r),
      (t = fl(t, "onChange")),
      0 < t.length && ((n = new Li("onChange", "change", null, n, r)), e.push({ event: n, listeners: t })));
  }
  var hr = null,
    mr = null;
  function fd(e) {
    Du(e, 0);
  }
  function sl(e) {
    var t = In(e);
    if (Es(t)) return e;
  }
  function dd(e, t) {
    if (e === "change") return t;
  }
  var yu = !1;
  if (y) {
    var zi;
    if (y) {
      var Fi = "oninput" in document;
      if (!Fi) {
        var gu = document.createElement("div");
        (gu.setAttribute("oninput", "return;"), (Fi = typeof gu.oninput == "function"));
      }
      zi = Fi;
    } else zi = !1;
    yu = zi && (!document.documentMode || 9 < document.documentMode);
  }
  function _u() {
    hr && (hr.detachEvent("onpropertychange", wu), (mr = hr = null));
  }
  function wu(e) {
    if (e.propertyName === "value" && sl(mr)) {
      var t = [];
      (vu(t, mr, e, vi(e)), $s(fd, t));
    }
  }
  function pd(e, t, n) {
    e === "focusin" ? (_u(), (hr = t), (mr = n), hr.attachEvent("onpropertychange", wu)) : e === "focusout" && _u();
  }
  function hd(e) {
    if (e === "selectionchange" || e === "keyup" || e === "keydown") return sl(mr);
  }
  function md(e, t) {
    if (e === "click") return sl(t);
  }
  function vd(e, t) {
    if (e === "input" || e === "change") return sl(t);
  }
  function yd(e, t) {
    return (e === t && (e !== 0 || 1 / e === 1 / t)) || (e !== e && t !== t);
  }
  var yt = typeof Object.is == "function" ? Object.is : yd;
  function vr(e, t) {
    if (yt(e, t)) return !0;
    if (typeof e != "object" || e === null || typeof t != "object" || t === null) return !1;
    var n = Object.keys(e),
      r = Object.keys(t);
    if (n.length !== r.length) return !1;
    for (r = 0; r < n.length; r++) {
      var l = n[r];
      if (!m.call(t, l) || !yt(e[l], t[l])) return !1;
    }
    return !0;
  }
  function xu(e) {
    for (; e && e.firstChild; ) e = e.firstChild;
    return e;
  }
  function Su(e, t) {
    var n = xu(e);
    e = 0;
    for (var r; n; ) {
      if (n.nodeType === 3) {
        if (((r = e + n.textContent.length), e <= t && r >= t)) return { node: n, offset: t - e };
        e = r;
      }
      e: {
        for (; n; ) {
          if (n.nextSibling) {
            n = n.nextSibling;
            break e;
          }
          n = n.parentNode;
        }
        n = void 0;
      }
      n = xu(n);
    }
  }
  function ku(e, t) {
    return e && t
      ? e === t
        ? !0
        : e && e.nodeType === 3
          ? !1
          : t && t.nodeType === 3
            ? ku(e, t.parentNode)
            : "contains" in e
              ? e.contains(t)
              : e.compareDocumentPosition
                ? !!(e.compareDocumentPosition(t) & 16)
                : !1
      : !1;
  }
  function Eu() {
    for (var e = window, t = Vr(); t instanceof e.HTMLIFrameElement; ) {
      try {
        var n = typeof t.contentWindow.location.href == "string";
      } catch {
        n = !1;
      }
      if (n) e = t.contentWindow;
      else break;
      t = Vr(e.document);
    }
    return t;
  }
  function Ai(e) {
    var t = e && e.nodeName && e.nodeName.toLowerCase();
    return (
      t &&
      ((t === "input" &&
        (e.type === "text" || e.type === "search" || e.type === "tel" || e.type === "url" || e.type === "password")) ||
        t === "textarea" ||
        e.contentEditable === "true")
    );
  }
  function gd(e) {
    var t = Eu(),
      n = e.focusedElem,
      r = e.selectionRange;
    if (t !== n && n && n.ownerDocument && ku(n.ownerDocument.documentElement, n)) {
      if (r !== null && Ai(n)) {
        if (((t = r.start), (e = r.end), e === void 0 && (e = t), "selectionStart" in n))
          ((n.selectionStart = t), (n.selectionEnd = Math.min(e, n.value.length)));
        else if (((e = ((t = n.ownerDocument || document) && t.defaultView) || window), e.getSelection)) {
          e = e.getSelection();
          var l = n.textContent.length,
            o = Math.min(r.start, l);
          ((r = r.end === void 0 ? o : Math.min(r.end, l)),
            !e.extend && o > r && ((l = r), (r = o), (o = l)),
            (l = Su(n, o)));
          var a = Su(n, r);
          l &&
            a &&
            (e.rangeCount !== 1 ||
              e.anchorNode !== l.node ||
              e.anchorOffset !== l.offset ||
              e.focusNode !== a.node ||
              e.focusOffset !== a.offset) &&
            ((t = t.createRange()),
            t.setStart(l.node, l.offset),
            e.removeAllRanges(),
            o > r ? (e.addRange(t), e.extend(a.node, a.offset)) : (t.setEnd(a.node, a.offset), e.addRange(t)));
        }
      }
      for (t = [], e = n; (e = e.parentNode); )
        e.nodeType === 1 && t.push({ element: e, left: e.scrollLeft, top: e.scrollTop });
      for (typeof n.focus == "function" && n.focus(), n = 0; n < t.length; n++)
        ((e = t[n]), (e.element.scrollLeft = e.left), (e.element.scrollTop = e.top));
    }
  }
  var _d = y && "documentMode" in document && 11 >= document.documentMode,
    Tn = null,
    Ui = null,
    yr = null,
    $i = !1;
  function Cu(e, t, n) {
    var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
    $i ||
      Tn == null ||
      Tn !== Vr(r) ||
      ((r = Tn),
      "selectionStart" in r && Ai(r)
        ? (r = { start: r.selectionStart, end: r.selectionEnd })
        : ((r = ((r.ownerDocument && r.ownerDocument.defaultView) || window).getSelection()),
          (r = {
            anchorNode: r.anchorNode,
            anchorOffset: r.anchorOffset,
            focusNode: r.focusNode,
            focusOffset: r.focusOffset,
          })),
      (yr && vr(yr, r)) ||
        ((yr = r),
        (r = fl(Ui, "onSelect")),
        0 < r.length &&
          ((t = new Li("onSelect", "select", null, t, n)), e.push({ event: t, listeners: r }), (t.target = Tn))));
  }
  function ul(e, t) {
    var n = {};
    return ((n[e.toLowerCase()] = t.toLowerCase()), (n["Webkit" + e] = "webkit" + t), (n["Moz" + e] = "moz" + t), n);
  }
  var On = {
      animationend: ul("Animation", "AnimationEnd"),
      animationiteration: ul("Animation", "AnimationIteration"),
      animationstart: ul("Animation", "AnimationStart"),
      transitionend: ul("Transition", "TransitionEnd"),
    },
    Bi = {},
    Nu = {};
  y &&
    ((Nu = document.createElement("div").style),
    "AnimationEvent" in window ||
      (delete On.animationend.animation, delete On.animationiteration.animation, delete On.animationstart.animation),
    "TransitionEvent" in window || delete On.transitionend.transition);
  function al(e) {
    if (Bi[e]) return Bi[e];
    if (!On[e]) return e;
    var t = On[e],
      n;
    for (n in t) if (t.hasOwnProperty(n) && n in Nu) return (Bi[e] = t[n]);
    return e;
  }
  var Ru = al("animationend"),
    ju = al("animationiteration"),
    Pu = al("animationstart"),
    Lu = al("transitionend"),
    Tu = new Map(),
    Ou =
      "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(
        " "
      );
  function Yt(e, t) {
    (Tu.set(e, t), d(t, [e]));
  }
  for (var Hi = 0; Hi < Ou.length; Hi++) {
    var Wi = Ou[Hi],
      wd = Wi.toLowerCase(),
      xd = Wi[0].toUpperCase() + Wi.slice(1);
    Yt(wd, "on" + xd);
  }
  (Yt(Ru, "onAnimationEnd"),
    Yt(ju, "onAnimationIteration"),
    Yt(Pu, "onAnimationStart"),
    Yt("dblclick", "onDoubleClick"),
    Yt("focusin", "onFocus"),
    Yt("focusout", "onBlur"),
    Yt(Lu, "onTransitionEnd"),
    h("onMouseEnter", ["mouseout", "mouseover"]),
    h("onMouseLeave", ["mouseout", "mouseover"]),
    h("onPointerEnter", ["pointerout", "pointerover"]),
    h("onPointerLeave", ["pointerout", "pointerover"]),
    d("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" ")),
    d("onSelect", "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")),
    d("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]),
    d("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" ")),
    d("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" ")),
    d("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" ")));
  var gr =
      "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(
        " "
      ),
    Sd = new Set("cancel close invalid load scroll toggle".split(" ").concat(gr));
  function Mu(e, t, n) {
    var r = e.type || "unknown-event";
    ((e.currentTarget = n), wf(r, t, void 0, e), (e.currentTarget = null));
  }
  function Du(e, t) {
    t = (t & 4) !== 0;
    for (var n = 0; n < e.length; n++) {
      var r = e[n],
        l = r.event;
      r = r.listeners;
      e: {
        var o = void 0;
        if (t)
          for (var a = r.length - 1; 0 <= a; a--) {
            var v = r[a],
              g = v.instance,
              N = v.currentTarget;
            if (((v = v.listener), g !== o && l.isPropagationStopped())) break e;
            (Mu(l, v, N), (o = g));
          }
        else
          for (a = 0; a < r.length; a++) {
            if (
              ((v = r[a]),
              (g = v.instance),
              (N = v.currentTarget),
              (v = v.listener),
              g !== o && l.isPropagationStopped())
            )
              break e;
            (Mu(l, v, N), (o = g));
          }
      }
    }
    if (qr) throw ((e = wi), (qr = !1), (wi = null), e);
  }
  function _e(e, t) {
    var n = t[Ji];
    n === void 0 && (n = t[Ji] = new Set());
    var r = e + "__bubble";
    n.has(r) || (Iu(t, e, 2, !1), n.add(r));
  }
  function Vi(e, t, n) {
    var r = 0;
    (t && (r |= 4), Iu(n, e, r, t));
  }
  var cl = "_reactListening" + Math.random().toString(36).slice(2);
  function _r(e) {
    if (!e[cl]) {
      ((e[cl] = !0),
        c.forEach(function (n) {
          n !== "selectionchange" && (Sd.has(n) || Vi(n, !1, e), Vi(n, !0, e));
        }));
      var t = e.nodeType === 9 ? e : e.ownerDocument;
      t === null || t[cl] || ((t[cl] = !0), Vi("selectionchange", !1, t));
    }
  }
  function Iu(e, t, n, r) {
    switch (lu(t)) {
      case 1:
        var l = zf;
        break;
      case 4:
        l = Ff;
        break;
      default:
        l = Ri;
    }
    ((n = l.bind(null, t, n, e)),
      (l = void 0),
      !_i || (t !== "touchstart" && t !== "touchmove" && t !== "wheel") || (l = !0),
      r
        ? l !== void 0
          ? e.addEventListener(t, n, { capture: !0, passive: l })
          : e.addEventListener(t, n, !0)
        : l !== void 0
          ? e.addEventListener(t, n, { passive: l })
          : e.addEventListener(t, n, !1));
  }
  function Qi(e, t, n, r, l) {
    var o = r;
    if ((t & 1) === 0 && (t & 2) === 0 && r !== null)
      e: for (;;) {
        if (r === null) return;
        var a = r.tag;
        if (a === 3 || a === 4) {
          var v = r.stateNode.containerInfo;
          if (v === l || (v.nodeType === 8 && v.parentNode === l)) break;
          if (a === 4)
            for (a = r.return; a !== null; ) {
              var g = a.tag;
              if (
                (g === 3 || g === 4) &&
                ((g = a.stateNode.containerInfo), g === l || (g.nodeType === 8 && g.parentNode === l))
              )
                return;
              a = a.return;
            }
          for (; v !== null; ) {
            if (((a = pn(v)), a === null)) return;
            if (((g = a.tag), g === 5 || g === 6)) {
              r = o = a;
              continue e;
            }
            v = v.parentNode;
          }
        }
        r = r.return;
      }
    $s(function () {
      var N = o,
        T = vi(n),
        O = [];
      e: {
        var P = Tu.get(e);
        if (P !== void 0) {
          var B = Li,
            Q = e;
          switch (e) {
            case "keypress":
              if (ll(n) === 0) break e;
            case "keydown":
            case "keyup":
              B = Zf;
              break;
            case "focusin":
              ((Q = "focus"), (B = Mi));
              break;
            case "focusout":
              ((Q = "blur"), (B = Mi));
              break;
            case "beforeblur":
            case "afterblur":
              B = Mi;
              break;
            case "click":
              if (n.button === 2) break e;
            case "auxclick":
            case "dblclick":
            case "mousedown":
            case "mousemove":
            case "mouseup":
            case "mouseout":
            case "mouseover":
            case "contextmenu":
              B = su;
              break;
            case "drag":
            case "dragend":
            case "dragenter":
            case "dragexit":
            case "dragleave":
            case "dragover":
            case "dragstart":
            case "drop":
              B = $f;
              break;
            case "touchcancel":
            case "touchend":
            case "touchmove":
            case "touchstart":
              B = td;
              break;
            case Ru:
            case ju:
            case Pu:
              B = Wf;
              break;
            case Lu:
              B = rd;
              break;
            case "scroll":
              B = Af;
              break;
            case "wheel":
              B = id;
              break;
            case "copy":
            case "cut":
            case "paste":
              B = Qf;
              break;
            case "gotpointercapture":
            case "lostpointercapture":
            case "pointercancel":
            case "pointerdown":
            case "pointermove":
            case "pointerout":
            case "pointerover":
            case "pointerup":
              B = au;
          }
          var K = (t & 4) !== 0,
            Le = !K && e === "scroll",
            k = K ? (P !== null ? P + "Capture" : null) : P;
          K = [];
          for (var _ = N, E; _ !== null; ) {
            E = _;
            var M = E.stateNode;
            if (
              (E.tag === 5 && M !== null && ((E = M), k !== null && ((M = tr(_, k)), M != null && K.push(wr(_, M, E)))),
              Le)
            )
              break;
            _ = _.return;
          }
          0 < K.length && ((P = new B(P, Q, null, n, T)), O.push({ event: P, listeners: K }));
        }
      }
      if ((t & 7) === 0) {
        e: {
          if (
            ((P = e === "mouseover" || e === "pointerover"),
            (B = e === "mouseout" || e === "pointerout"),
            P && n !== mi && (Q = n.relatedTarget || n.fromElement) && (pn(Q) || Q[Tt]))
          )
            break e;
          if (
            (B || P) &&
            ((P = T.window === T ? T : (P = T.ownerDocument) ? P.defaultView || P.parentWindow : window),
            B
              ? ((Q = n.relatedTarget || n.toElement),
                (B = N),
                (Q = Q ? pn(Q) : null),
                Q !== null && ((Le = dn(Q)), Q !== Le || (Q.tag !== 5 && Q.tag !== 6)) && (Q = null))
              : ((B = null), (Q = N)),
            B !== Q)
          ) {
            if (
              ((K = su),
              (M = "onMouseLeave"),
              (k = "onMouseEnter"),
              (_ = "mouse"),
              (e === "pointerout" || e === "pointerover") &&
                ((K = au), (M = "onPointerLeave"), (k = "onPointerEnter"), (_ = "pointer")),
              (Le = B == null ? P : In(B)),
              (E = Q == null ? P : In(Q)),
              (P = new K(M, _ + "leave", B, n, T)),
              (P.target = Le),
              (P.relatedTarget = E),
              (M = null),
              pn(T) === N && ((K = new K(k, _ + "enter", Q, n, T)), (K.target = E), (K.relatedTarget = Le), (M = K)),
              (Le = M),
              B && Q)
            )
              t: {
                for (K = B, k = Q, _ = 0, E = K; E; E = Mn(E)) _++;
                for (E = 0, M = k; M; M = Mn(M)) E++;
                for (; 0 < _ - E; ) ((K = Mn(K)), _--);
                for (; 0 < E - _; ) ((k = Mn(k)), E--);
                for (; _--; ) {
                  if (K === k || (k !== null && K === k.alternate)) break t;
                  ((K = Mn(K)), (k = Mn(k)));
                }
                K = null;
              }
            else K = null;
            (B !== null && zu(O, P, B, K, !1), Q !== null && Le !== null && zu(O, Le, Q, K, !0));
          }
        }
        e: {
          if (
            ((P = N ? In(N) : window),
            (B = P.nodeName && P.nodeName.toLowerCase()),
            B === "select" || (B === "input" && P.type === "file"))
          )
            var q = dd;
          else if (mu(P))
            if (yu) q = vd;
            else {
              q = hd;
              var X = pd;
            }
          else
            (B = P.nodeName) &&
              B.toLowerCase() === "input" &&
              (P.type === "checkbox" || P.type === "radio") &&
              (q = md);
          if (q && (q = q(e, N))) {
            vu(O, q, n, T);
            break e;
          }
          (X && X(e, P, N),
            e === "focusout" &&
              (X = P._wrapperState) &&
              X.controlled &&
              P.type === "number" &&
              ci(P, "number", P.value));
        }
        switch (((X = N ? In(N) : window), e)) {
          case "focusin":
            (mu(X) || X.contentEditable === "true") && ((Tn = X), (Ui = N), (yr = null));
            break;
          case "focusout":
            yr = Ui = Tn = null;
            break;
          case "mousedown":
            $i = !0;
            break;
          case "contextmenu":
          case "mouseup":
          case "dragend":
            (($i = !1), Cu(O, n, T));
            break;
          case "selectionchange":
            if (_d) break;
          case "keydown":
          case "keyup":
            Cu(O, n, T);
        }
        var J;
        if (Ii)
          e: {
            switch (e) {
              case "compositionstart":
                var Z = "onCompositionStart";
                break e;
              case "compositionend":
                Z = "onCompositionEnd";
                break e;
              case "compositionupdate":
                Z = "onCompositionUpdate";
                break e;
            }
            Z = void 0;
          }
        else
          Ln
            ? pu(e, n) && (Z = "onCompositionEnd")
            : e === "keydown" && n.keyCode === 229 && (Z = "onCompositionStart");
        (Z &&
          (cu &&
            n.locale !== "ko" &&
            (Ln || Z !== "onCompositionStart"
              ? Z === "onCompositionEnd" && Ln && (J = iu())
              : ((qt = T), (Pi = "value" in qt ? qt.value : qt.textContent), (Ln = !0))),
          (X = fl(N, Z)),
          0 < X.length &&
            ((Z = new uu(Z, e, null, n, T)),
            O.push({ event: Z, listeners: X }),
            J ? (Z.data = J) : ((J = hu(n)), J !== null && (Z.data = J)))),
          (J = sd ? ud(e, n) : ad(e, n)) &&
            ((N = fl(N, "onBeforeInput")),
            0 < N.length &&
              ((T = new uu("onBeforeInput", "beforeinput", null, n, T)),
              O.push({ event: T, listeners: N }),
              (T.data = J))));
      }
      Du(O, t);
    });
  }
  function wr(e, t, n) {
    return { instance: e, listener: t, currentTarget: n };
  }
  function fl(e, t) {
    for (var n = t + "Capture", r = []; e !== null; ) {
      var l = e,
        o = l.stateNode;
      (l.tag === 5 &&
        o !== null &&
        ((l = o),
        (o = tr(e, n)),
        o != null && r.unshift(wr(e, o, l)),
        (o = tr(e, t)),
        o != null && r.push(wr(e, o, l))),
        (e = e.return));
    }
    return r;
  }
  function Mn(e) {
    if (e === null) return null;
    do e = e.return;
    while (e && e.tag !== 5);
    return e || null;
  }
  function zu(e, t, n, r, l) {
    for (var o = t._reactName, a = []; n !== null && n !== r; ) {
      var v = n,
        g = v.alternate,
        N = v.stateNode;
      if (g !== null && g === r) break;
      (v.tag === 5 &&
        N !== null &&
        ((v = N),
        l
          ? ((g = tr(n, o)), g != null && a.unshift(wr(n, g, v)))
          : l || ((g = tr(n, o)), g != null && a.push(wr(n, g, v)))),
        (n = n.return));
    }
    a.length !== 0 && e.push({ event: t, listeners: a });
  }
  var kd = /\r\n?/g,
    Ed = /\u0000|\uFFFD/g;
  function Fu(e) {
    return (typeof e == "string" ? e : "" + e)
      .replace(
        kd,
        `
`
      )
      .replace(Ed, "");
  }
  function dl(e, t, n) {
    if (((t = Fu(t)), Fu(e) !== t && n)) throw Error(s(425));
  }
  function pl() {}
  var Ki = null,
    qi = null;
  function Yi(e, t) {
    return (
      e === "textarea" ||
      e === "noscript" ||
      typeof t.children == "string" ||
      typeof t.children == "number" ||
      (typeof t.dangerouslySetInnerHTML == "object" &&
        t.dangerouslySetInnerHTML !== null &&
        t.dangerouslySetInnerHTML.__html != null)
    );
  }
  var Gi = typeof setTimeout == "function" ? setTimeout : void 0,
    Cd = typeof clearTimeout == "function" ? clearTimeout : void 0,
    Au = typeof Promise == "function" ? Promise : void 0,
    Nd =
      typeof queueMicrotask == "function"
        ? queueMicrotask
        : typeof Au < "u"
          ? function (e) {
              return Au.resolve(null).then(e).catch(Rd);
            }
          : Gi;
  function Rd(e) {
    setTimeout(function () {
      throw e;
    });
  }
  function Xi(e, t) {
    var n = t,
      r = 0;
    do {
      var l = n.nextSibling;
      if ((e.removeChild(n), l && l.nodeType === 8))
        if (((n = l.data), n === "/$")) {
          if (r === 0) {
            (e.removeChild(l), cr(t));
            return;
          }
          r--;
        } else (n !== "$" && n !== "$?" && n !== "$!") || r++;
      n = l;
    } while (n);
    cr(t);
  }
  function Gt(e) {
    for (; e != null; e = e.nextSibling) {
      var t = e.nodeType;
      if (t === 1 || t === 3) break;
      if (t === 8) {
        if (((t = e.data), t === "$" || t === "$!" || t === "$?")) break;
        if (t === "/$") return null;
      }
    }
    return e;
  }
  function Uu(e) {
    e = e.previousSibling;
    for (var t = 0; e; ) {
      if (e.nodeType === 8) {
        var n = e.data;
        if (n === "$" || n === "$!" || n === "$?") {
          if (t === 0) return e;
          t--;
        } else n === "/$" && t++;
      }
      e = e.previousSibling;
    }
    return null;
  }
  var Dn = Math.random().toString(36).slice(2),
    Ct = "__reactFiber$" + Dn,
    xr = "__reactProps$" + Dn,
    Tt = "__reactContainer$" + Dn,
    Ji = "__reactEvents$" + Dn,
    jd = "__reactListeners$" + Dn,
    Pd = "__reactHandles$" + Dn;
  function pn(e) {
    var t = e[Ct];
    if (t) return t;
    for (var n = e.parentNode; n; ) {
      if ((t = n[Tt] || n[Ct])) {
        if (((n = t.alternate), t.child !== null || (n !== null && n.child !== null)))
          for (e = Uu(e); e !== null; ) {
            if ((n = e[Ct])) return n;
            e = Uu(e);
          }
        return t;
      }
      ((e = n), (n = e.parentNode));
    }
    return null;
  }
  function Sr(e) {
    return ((e = e[Ct] || e[Tt]), !e || (e.tag !== 5 && e.tag !== 6 && e.tag !== 13 && e.tag !== 3) ? null : e);
  }
  function In(e) {
    if (e.tag === 5 || e.tag === 6) return e.stateNode;
    throw Error(s(33));
  }
  function hl(e) {
    return e[xr] || null;
  }
  var Zi = [],
    zn = -1;
  function Xt(e) {
    return { current: e };
  }
  function we(e) {
    0 > zn || ((e.current = Zi[zn]), (Zi[zn] = null), zn--);
  }
  function ye(e, t) {
    (zn++, (Zi[zn] = e.current), (e.current = t));
  }
  var Jt = {},
    We = Xt(Jt),
    Xe = Xt(!1),
    hn = Jt;
  function Fn(e, t) {
    var n = e.type.contextTypes;
    if (!n) return Jt;
    var r = e.stateNode;
    if (r && r.__reactInternalMemoizedUnmaskedChildContext === t) return r.__reactInternalMemoizedMaskedChildContext;
    var l = {},
      o;
    for (o in n) l[o] = t[o];
    return (
      r &&
        ((e = e.stateNode),
        (e.__reactInternalMemoizedUnmaskedChildContext = t),
        (e.__reactInternalMemoizedMaskedChildContext = l)),
      l
    );
  }
  function Je(e) {
    return ((e = e.childContextTypes), e != null);
  }
  function ml() {
    (we(Xe), we(We));
  }
  function $u(e, t, n) {
    if (We.current !== Jt) throw Error(s(168));
    (ye(We, t), ye(Xe, n));
  }
  function Bu(e, t, n) {
    var r = e.stateNode;
    if (((t = t.childContextTypes), typeof r.getChildContext != "function")) return n;
    r = r.getChildContext();
    for (var l in r) if (!(l in t)) throw Error(s(108, ve(e) || "Unknown", l));
    return H({}, n, r);
  }
  function vl(e) {
    return (
      (e = ((e = e.stateNode) && e.__reactInternalMemoizedMergedChildContext) || Jt),
      (hn = We.current),
      ye(We, e),
      ye(Xe, Xe.current),
      !0
    );
  }
  function Hu(e, t, n) {
    var r = e.stateNode;
    if (!r) throw Error(s(169));
    (n ? ((e = Bu(e, t, hn)), (r.__reactInternalMemoizedMergedChildContext = e), we(Xe), we(We), ye(We, e)) : we(Xe),
      ye(Xe, n));
  }
  var Ot = null,
    yl = !1,
    bi = !1;
  function Wu(e) {
    Ot === null ? (Ot = [e]) : Ot.push(e);
  }
  function Ld(e) {
    ((yl = !0), Wu(e));
  }
  function Zt() {
    if (!bi && Ot !== null) {
      bi = !0;
      var e = 0,
        t = pe;
      try {
        var n = Ot;
        for (pe = 1; e < n.length; e++) {
          var r = n[e];
          do r = r(!0);
          while (r !== null);
        }
        ((Ot = null), (yl = !1));
      } catch (l) {
        throw (Ot !== null && (Ot = Ot.slice(e + 1)), Qs(xi, Zt), l);
      } finally {
        ((pe = t), (bi = !1));
      }
    }
    return null;
  }
  var An = [],
    Un = 0,
    gl = null,
    _l = 0,
    ut = [],
    at = 0,
    mn = null,
    Mt = 1,
    Dt = "";
  function vn(e, t) {
    ((An[Un++] = _l), (An[Un++] = gl), (gl = e), (_l = t));
  }
  function Vu(e, t, n) {
    ((ut[at++] = Mt), (ut[at++] = Dt), (ut[at++] = mn), (mn = e));
    var r = Mt;
    e = Dt;
    var l = 32 - vt(r) - 1;
    ((r &= ~(1 << l)), (n += 1));
    var o = 32 - vt(t) + l;
    if (30 < o) {
      var a = l - (l % 5);
      ((o = (r & ((1 << a) - 1)).toString(32)),
        (r >>= a),
        (l -= a),
        (Mt = (1 << (32 - vt(t) + l)) | (n << l) | r),
        (Dt = o + e));
    } else ((Mt = (1 << o) | (n << l) | r), (Dt = e));
  }
  function eo(e) {
    e.return !== null && (vn(e, 1), Vu(e, 1, 0));
  }
  function to(e) {
    for (; e === gl; ) ((gl = An[--Un]), (An[Un] = null), (_l = An[--Un]), (An[Un] = null));
    for (; e === mn; )
      ((mn = ut[--at]), (ut[at] = null), (Dt = ut[--at]), (ut[at] = null), (Mt = ut[--at]), (ut[at] = null));
  }
  var lt = null,
    it = null,
    ke = !1,
    gt = null;
  function Qu(e, t) {
    var n = pt(5, null, null, 0);
    ((n.elementType = "DELETED"),
      (n.stateNode = t),
      (n.return = e),
      (t = e.deletions),
      t === null ? ((e.deletions = [n]), (e.flags |= 16)) : t.push(n));
  }
  function Ku(e, t) {
    switch (e.tag) {
      case 5:
        var n = e.type;
        return (
          (t = t.nodeType !== 1 || n.toLowerCase() !== t.nodeName.toLowerCase() ? null : t),
          t !== null ? ((e.stateNode = t), (lt = e), (it = Gt(t.firstChild)), !0) : !1
        );
      case 6:
        return (
          (t = e.pendingProps === "" || t.nodeType !== 3 ? null : t),
          t !== null ? ((e.stateNode = t), (lt = e), (it = null), !0) : !1
        );
      case 13:
        return (
          (t = t.nodeType !== 8 ? null : t),
          t !== null
            ? ((n = mn !== null ? { id: Mt, overflow: Dt } : null),
              (e.memoizedState = { dehydrated: t, treeContext: n, retryLane: 1073741824 }),
              (n = pt(18, null, null, 0)),
              (n.stateNode = t),
              (n.return = e),
              (e.child = n),
              (lt = e),
              (it = null),
              !0)
            : !1
        );
      default:
        return !1;
    }
  }
  function no(e) {
    return (e.mode & 1) !== 0 && (e.flags & 128) === 0;
  }
  function ro(e) {
    if (ke) {
      var t = it;
      if (t) {
        var n = t;
        if (!Ku(e, t)) {
          if (no(e)) throw Error(s(418));
          t = Gt(n.nextSibling);
          var r = lt;
          t && Ku(e, t) ? Qu(r, n) : ((e.flags = (e.flags & -4097) | 2), (ke = !1), (lt = e));
        }
      } else {
        if (no(e)) throw Error(s(418));
        ((e.flags = (e.flags & -4097) | 2), (ke = !1), (lt = e));
      }
    }
  }
  function qu(e) {
    for (e = e.return; e !== null && e.tag !== 5 && e.tag !== 3 && e.tag !== 13; ) e = e.return;
    lt = e;
  }
  function wl(e) {
    if (e !== lt) return !1;
    if (!ke) return (qu(e), (ke = !0), !1);
    var t;
    if (
      ((t = e.tag !== 3) &&
        !(t = e.tag !== 5) &&
        ((t = e.type), (t = t !== "head" && t !== "body" && !Yi(e.type, e.memoizedProps))),
      t && (t = it))
    ) {
      if (no(e)) throw (Yu(), Error(s(418)));
      for (; t; ) (Qu(e, t), (t = Gt(t.nextSibling)));
    }
    if ((qu(e), e.tag === 13)) {
      if (((e = e.memoizedState), (e = e !== null ? e.dehydrated : null), !e)) throw Error(s(317));
      e: {
        for (e = e.nextSibling, t = 0; e; ) {
          if (e.nodeType === 8) {
            var n = e.data;
            if (n === "/$") {
              if (t === 0) {
                it = Gt(e.nextSibling);
                break e;
              }
              t--;
            } else (n !== "$" && n !== "$!" && n !== "$?") || t++;
          }
          e = e.nextSibling;
        }
        it = null;
      }
    } else it = lt ? Gt(e.stateNode.nextSibling) : null;
    return !0;
  }
  function Yu() {
    for (var e = it; e; ) e = Gt(e.nextSibling);
  }
  function $n() {
    ((it = lt = null), (ke = !1));
  }
  function lo(e) {
    gt === null ? (gt = [e]) : gt.push(e);
  }
  var Td = le.ReactCurrentBatchConfig;
  function kr(e, t, n) {
    if (((e = n.ref), e !== null && typeof e != "function" && typeof e != "object")) {
      if (n._owner) {
        if (((n = n._owner), n)) {
          if (n.tag !== 1) throw Error(s(309));
          var r = n.stateNode;
        }
        if (!r) throw Error(s(147, e));
        var l = r,
          o = "" + e;
        return t !== null && t.ref !== null && typeof t.ref == "function" && t.ref._stringRef === o
          ? t.ref
          : ((t = function (a) {
              var v = l.refs;
              a === null ? delete v[o] : (v[o] = a);
            }),
            (t._stringRef = o),
            t);
      }
      if (typeof e != "string") throw Error(s(284));
      if (!n._owner) throw Error(s(290, e));
    }
    return e;
  }
  function xl(e, t) {
    throw (
      (e = Object.prototype.toString.call(t)),
      Error(s(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e))
    );
  }
  function Gu(e) {
    var t = e._init;
    return t(e._payload);
  }
  function Xu(e) {
    function t(k, _) {
      if (e) {
        var E = k.deletions;
        E === null ? ((k.deletions = [_]), (k.flags |= 16)) : E.push(_);
      }
    }
    function n(k, _) {
      if (!e) return null;
      for (; _ !== null; ) (t(k, _), (_ = _.sibling));
      return null;
    }
    function r(k, _) {
      for (k = new Map(); _ !== null; ) (_.key !== null ? k.set(_.key, _) : k.set(_.index, _), (_ = _.sibling));
      return k;
    }
    function l(k, _) {
      return ((k = sn(k, _)), (k.index = 0), (k.sibling = null), k);
    }
    function o(k, _, E) {
      return (
        (k.index = E),
        e
          ? ((E = k.alternate), E !== null ? ((E = E.index), E < _ ? ((k.flags |= 2), _) : E) : ((k.flags |= 2), _))
          : ((k.flags |= 1048576), _)
      );
    }
    function a(k) {
      return (e && k.alternate === null && (k.flags |= 2), k);
    }
    function v(k, _, E, M) {
      return _ === null || _.tag !== 6
        ? ((_ = Xo(E, k.mode, M)), (_.return = k), _)
        : ((_ = l(_, E)), (_.return = k), _);
    }
    function g(k, _, E, M) {
      var q = E.type;
      return q === xe
        ? T(k, _, E.props.children, M, E.key)
        : _ !== null &&
            (_.elementType === q || (typeof q == "object" && q !== null && q.$$typeof === me && Gu(q) === _.type))
          ? ((M = l(_, E.props)), (M.ref = kr(k, _, E)), (M.return = k), M)
          : ((M = Ql(E.type, E.key, E.props, null, k.mode, M)), (M.ref = kr(k, _, E)), (M.return = k), M);
    }
    function N(k, _, E, M) {
      return _ === null ||
        _.tag !== 4 ||
        _.stateNode.containerInfo !== E.containerInfo ||
        _.stateNode.implementation !== E.implementation
        ? ((_ = Jo(E, k.mode, M)), (_.return = k), _)
        : ((_ = l(_, E.children || [])), (_.return = k), _);
    }
    function T(k, _, E, M, q) {
      return _ === null || _.tag !== 7
        ? ((_ = En(E, k.mode, M, q)), (_.return = k), _)
        : ((_ = l(_, E)), (_.return = k), _);
    }
    function O(k, _, E) {
      if ((typeof _ == "string" && _ !== "") || typeof _ == "number")
        return ((_ = Xo("" + _, k.mode, E)), (_.return = k), _);
      if (typeof _ == "object" && _ !== null) {
        switch (_.$$typeof) {
          case ie:
            return ((E = Ql(_.type, _.key, _.props, null, k.mode, E)), (E.ref = kr(k, null, _)), (E.return = k), E);
          case he:
            return ((_ = Jo(_, k.mode, E)), (_.return = k), _);
          case me:
            var M = _._init;
            return O(k, M(_._payload), E);
        }
        if (Zn(_) || Y(_)) return ((_ = En(_, k.mode, E, null)), (_.return = k), _);
        xl(k, _);
      }
      return null;
    }
    function P(k, _, E, M) {
      var q = _ !== null ? _.key : null;
      if ((typeof E == "string" && E !== "") || typeof E == "number") return q !== null ? null : v(k, _, "" + E, M);
      if (typeof E == "object" && E !== null) {
        switch (E.$$typeof) {
          case ie:
            return E.key === q ? g(k, _, E, M) : null;
          case he:
            return E.key === q ? N(k, _, E, M) : null;
          case me:
            return ((q = E._init), P(k, _, q(E._payload), M));
        }
        if (Zn(E) || Y(E)) return q !== null ? null : T(k, _, E, M, null);
        xl(k, E);
      }
      return null;
    }
    function B(k, _, E, M, q) {
      if ((typeof M == "string" && M !== "") || typeof M == "number")
        return ((k = k.get(E) || null), v(_, k, "" + M, q));
      if (typeof M == "object" && M !== null) {
        switch (M.$$typeof) {
          case ie:
            return ((k = k.get(M.key === null ? E : M.key) || null), g(_, k, M, q));
          case he:
            return ((k = k.get(M.key === null ? E : M.key) || null), N(_, k, M, q));
          case me:
            var X = M._init;
            return B(k, _, E, X(M._payload), q);
        }
        if (Zn(M) || Y(M)) return ((k = k.get(E) || null), T(_, k, M, q, null));
        xl(_, M);
      }
      return null;
    }
    function Q(k, _, E, M) {
      for (var q = null, X = null, J = _, Z = (_ = 0), $e = null; J !== null && Z < E.length; Z++) {
        J.index > Z ? (($e = J), (J = null)) : ($e = J.sibling);
        var ce = P(k, J, E[Z], M);
        if (ce === null) {
          J === null && (J = $e);
          break;
        }
        (e && J && ce.alternate === null && t(k, J),
          (_ = o(ce, _, Z)),
          X === null ? (q = ce) : (X.sibling = ce),
          (X = ce),
          (J = $e));
      }
      if (Z === E.length) return (n(k, J), ke && vn(k, Z), q);
      if (J === null) {
        for (; Z < E.length; Z++)
          ((J = O(k, E[Z], M)), J !== null && ((_ = o(J, _, Z)), X === null ? (q = J) : (X.sibling = J), (X = J)));
        return (ke && vn(k, Z), q);
      }
      for (J = r(k, J); Z < E.length; Z++)
        (($e = B(J, k, Z, E[Z], M)),
          $e !== null &&
            (e && $e.alternate !== null && J.delete($e.key === null ? Z : $e.key),
            (_ = o($e, _, Z)),
            X === null ? (q = $e) : (X.sibling = $e),
            (X = $e)));
      return (
        e &&
          J.forEach(function (un) {
            return t(k, un);
          }),
        ke && vn(k, Z),
        q
      );
    }
    function K(k, _, E, M) {
      var q = Y(E);
      if (typeof q != "function") throw Error(s(150));
      if (((E = q.call(E)), E == null)) throw Error(s(151));
      for (
        var X = (q = null), J = _, Z = (_ = 0), $e = null, ce = E.next();
        J !== null && !ce.done;
        Z++, ce = E.next()
      ) {
        J.index > Z ? (($e = J), (J = null)) : ($e = J.sibling);
        var un = P(k, J, ce.value, M);
        if (un === null) {
          J === null && (J = $e);
          break;
        }
        (e && J && un.alternate === null && t(k, J),
          (_ = o(un, _, Z)),
          X === null ? (q = un) : (X.sibling = un),
          (X = un),
          (J = $e));
      }
      if (ce.done) return (n(k, J), ke && vn(k, Z), q);
      if (J === null) {
        for (; !ce.done; Z++, ce = E.next())
          ((ce = O(k, ce.value, M)),
            ce !== null && ((_ = o(ce, _, Z)), X === null ? (q = ce) : (X.sibling = ce), (X = ce)));
        return (ke && vn(k, Z), q);
      }
      for (J = r(k, J); !ce.done; Z++, ce = E.next())
        ((ce = B(J, k, Z, ce.value, M)),
          ce !== null &&
            (e && ce.alternate !== null && J.delete(ce.key === null ? Z : ce.key),
            (_ = o(ce, _, Z)),
            X === null ? (q = ce) : (X.sibling = ce),
            (X = ce)));
      return (
        e &&
          J.forEach(function (cp) {
            return t(k, cp);
          }),
        ke && vn(k, Z),
        q
      );
    }
    function Le(k, _, E, M) {
      if (
        (typeof E == "object" && E !== null && E.type === xe && E.key === null && (E = E.props.children),
        typeof E == "object" && E !== null)
      ) {
        switch (E.$$typeof) {
          case ie:
            e: {
              for (var q = E.key, X = _; X !== null; ) {
                if (X.key === q) {
                  if (((q = E.type), q === xe)) {
                    if (X.tag === 7) {
                      (n(k, X.sibling), (_ = l(X, E.props.children)), (_.return = k), (k = _));
                      break e;
                    }
                  } else if (
                    X.elementType === q ||
                    (typeof q == "object" && q !== null && q.$$typeof === me && Gu(q) === X.type)
                  ) {
                    (n(k, X.sibling), (_ = l(X, E.props)), (_.ref = kr(k, X, E)), (_.return = k), (k = _));
                    break e;
                  }
                  n(k, X);
                  break;
                } else t(k, X);
                X = X.sibling;
              }
              E.type === xe
                ? ((_ = En(E.props.children, k.mode, M, E.key)), (_.return = k), (k = _))
                : ((M = Ql(E.type, E.key, E.props, null, k.mode, M)), (M.ref = kr(k, _, E)), (M.return = k), (k = M));
            }
            return a(k);
          case he:
            e: {
              for (X = E.key; _ !== null; ) {
                if (_.key === X)
                  if (
                    _.tag === 4 &&
                    _.stateNode.containerInfo === E.containerInfo &&
                    _.stateNode.implementation === E.implementation
                  ) {
                    (n(k, _.sibling), (_ = l(_, E.children || [])), (_.return = k), (k = _));
                    break e;
                  } else {
                    n(k, _);
                    break;
                  }
                else t(k, _);
                _ = _.sibling;
              }
              ((_ = Jo(E, k.mode, M)), (_.return = k), (k = _));
            }
            return a(k);
          case me:
            return ((X = E._init), Le(k, _, X(E._payload), M));
        }
        if (Zn(E)) return Q(k, _, E, M);
        if (Y(E)) return K(k, _, E, M);
        xl(k, E);
      }
      return (typeof E == "string" && E !== "") || typeof E == "number"
        ? ((E = "" + E),
          _ !== null && _.tag === 6
            ? (n(k, _.sibling), (_ = l(_, E)), (_.return = k), (k = _))
            : (n(k, _), (_ = Xo(E, k.mode, M)), (_.return = k), (k = _)),
          a(k))
        : n(k, _);
    }
    return Le;
  }
  var Bn = Xu(!0),
    Ju = Xu(!1),
    Sl = Xt(null),
    kl = null,
    Hn = null,
    io = null;
  function oo() {
    io = Hn = kl = null;
  }
  function so(e) {
    var t = Sl.current;
    (we(Sl), (e._currentValue = t));
  }
  function uo(e, t, n) {
    for (; e !== null; ) {
      var r = e.alternate;
      if (
        ((e.childLanes & t) !== t
          ? ((e.childLanes |= t), r !== null && (r.childLanes |= t))
          : r !== null && (r.childLanes & t) !== t && (r.childLanes |= t),
        e === n)
      )
        break;
      e = e.return;
    }
  }
  function Wn(e, t) {
    ((kl = e),
      (io = Hn = null),
      (e = e.dependencies),
      e !== null && e.firstContext !== null && ((e.lanes & t) !== 0 && (Ze = !0), (e.firstContext = null)));
  }
  function ct(e) {
    var t = e._currentValue;
    if (io !== e)
      if (((e = { context: e, memoizedValue: t, next: null }), Hn === null)) {
        if (kl === null) throw Error(s(308));
        ((Hn = e), (kl.dependencies = { lanes: 0, firstContext: e }));
      } else Hn = Hn.next = e;
    return t;
  }
  var yn = null;
  function ao(e) {
    yn === null ? (yn = [e]) : yn.push(e);
  }
  function Zu(e, t, n, r) {
    var l = t.interleaved;
    return (l === null ? ((n.next = n), ao(t)) : ((n.next = l.next), (l.next = n)), (t.interleaved = n), It(e, r));
  }
  function It(e, t) {
    e.lanes |= t;
    var n = e.alternate;
    for (n !== null && (n.lanes |= t), n = e, e = e.return; e !== null; )
      ((e.childLanes |= t), (n = e.alternate), n !== null && (n.childLanes |= t), (n = e), (e = e.return));
    return n.tag === 3 ? n.stateNode : null;
  }
  var bt = !1;
  function co(e) {
    e.updateQueue = {
      baseState: e.memoizedState,
      firstBaseUpdate: null,
      lastBaseUpdate: null,
      shared: { pending: null, interleaved: null, lanes: 0 },
      effects: null,
    };
  }
  function bu(e, t) {
    ((e = e.updateQueue),
      t.updateQueue === e &&
        (t.updateQueue = {
          baseState: e.baseState,
          firstBaseUpdate: e.firstBaseUpdate,
          lastBaseUpdate: e.lastBaseUpdate,
          shared: e.shared,
          effects: e.effects,
        }));
  }
  function zt(e, t) {
    return { eventTime: e, lane: t, tag: 0, payload: null, callback: null, next: null };
  }
  function en(e, t, n) {
    var r = e.updateQueue;
    if (r === null) return null;
    if (((r = r.shared), (se & 2) !== 0)) {
      var l = r.pending;
      return (l === null ? (t.next = t) : ((t.next = l.next), (l.next = t)), (r.pending = t), It(e, n));
    }
    return (
      (l = r.interleaved),
      l === null ? ((t.next = t), ao(r)) : ((t.next = l.next), (l.next = t)),
      (r.interleaved = t),
      It(e, n)
    );
  }
  function El(e, t, n) {
    if (((t = t.updateQueue), t !== null && ((t = t.shared), (n & 4194240) !== 0))) {
      var r = t.lanes;
      ((r &= e.pendingLanes), (n |= r), (t.lanes = n), Ei(e, n));
    }
  }
  function ea(e, t) {
    var n = e.updateQueue,
      r = e.alternate;
    if (r !== null && ((r = r.updateQueue), n === r)) {
      var l = null,
        o = null;
      if (((n = n.firstBaseUpdate), n !== null)) {
        do {
          var a = {
            eventTime: n.eventTime,
            lane: n.lane,
            tag: n.tag,
            payload: n.payload,
            callback: n.callback,
            next: null,
          };
          (o === null ? (l = o = a) : (o = o.next = a), (n = n.next));
        } while (n !== null);
        o === null ? (l = o = t) : (o = o.next = t);
      } else l = o = t;
      ((n = { baseState: r.baseState, firstBaseUpdate: l, lastBaseUpdate: o, shared: r.shared, effects: r.effects }),
        (e.updateQueue = n));
      return;
    }
    ((e = n.lastBaseUpdate), e === null ? (n.firstBaseUpdate = t) : (e.next = t), (n.lastBaseUpdate = t));
  }
  function Cl(e, t, n, r) {
    var l = e.updateQueue;
    bt = !1;
    var o = l.firstBaseUpdate,
      a = l.lastBaseUpdate,
      v = l.shared.pending;
    if (v !== null) {
      l.shared.pending = null;
      var g = v,
        N = g.next;
      ((g.next = null), a === null ? (o = N) : (a.next = N), (a = g));
      var T = e.alternate;
      T !== null &&
        ((T = T.updateQueue),
        (v = T.lastBaseUpdate),
        v !== a && (v === null ? (T.firstBaseUpdate = N) : (v.next = N), (T.lastBaseUpdate = g)));
    }
    if (o !== null) {
      var O = l.baseState;
      ((a = 0), (T = N = g = null), (v = o));
      do {
        var P = v.lane,
          B = v.eventTime;
        if ((r & P) === P) {
          T !== null &&
            (T = T.next = { eventTime: B, lane: 0, tag: v.tag, payload: v.payload, callback: v.callback, next: null });
          e: {
            var Q = e,
              K = v;
            switch (((P = t), (B = n), K.tag)) {
              case 1:
                if (((Q = K.payload), typeof Q == "function")) {
                  O = Q.call(B, O, P);
                  break e;
                }
                O = Q;
                break e;
              case 3:
                Q.flags = (Q.flags & -65537) | 128;
              case 0:
                if (((Q = K.payload), (P = typeof Q == "function" ? Q.call(B, O, P) : Q), P == null)) break e;
                O = H({}, O, P);
                break e;
              case 2:
                bt = !0;
            }
          }
          v.callback !== null &&
            v.lane !== 0 &&
            ((e.flags |= 64), (P = l.effects), P === null ? (l.effects = [v]) : P.push(v));
        } else
          ((B = { eventTime: B, lane: P, tag: v.tag, payload: v.payload, callback: v.callback, next: null }),
            T === null ? ((N = T = B), (g = O)) : (T = T.next = B),
            (a |= P));
        if (((v = v.next), v === null)) {
          if (((v = l.shared.pending), v === null)) break;
          ((P = v), (v = P.next), (P.next = null), (l.lastBaseUpdate = P), (l.shared.pending = null));
        }
      } while (!0);
      if (
        (T === null && (g = O),
        (l.baseState = g),
        (l.firstBaseUpdate = N),
        (l.lastBaseUpdate = T),
        (t = l.shared.interleaved),
        t !== null)
      ) {
        l = t;
        do ((a |= l.lane), (l = l.next));
        while (l !== t);
      } else o === null && (l.shared.lanes = 0);
      ((wn |= a), (e.lanes = a), (e.memoizedState = O));
    }
  }
  function ta(e, t, n) {
    if (((e = t.effects), (t.effects = null), e !== null))
      for (t = 0; t < e.length; t++) {
        var r = e[t],
          l = r.callback;
        if (l !== null) {
          if (((r.callback = null), (r = n), typeof l != "function")) throw Error(s(191, l));
          l.call(r);
        }
      }
  }
  var Er = {},
    Nt = Xt(Er),
    Cr = Xt(Er),
    Nr = Xt(Er);
  function gn(e) {
    if (e === Er) throw Error(s(174));
    return e;
  }
  function fo(e, t) {
    switch ((ye(Nr, t), ye(Cr, e), ye(Nt, Er), (e = t.nodeType), e)) {
      case 9:
      case 11:
        t = (t = t.documentElement) ? t.namespaceURI : di(null, "");
        break;
      default:
        ((e = e === 8 ? t.parentNode : t), (t = e.namespaceURI || null), (e = e.tagName), (t = di(t, e)));
    }
    (we(Nt), ye(Nt, t));
  }
  function Vn() {
    (we(Nt), we(Cr), we(Nr));
  }
  function na(e) {
    gn(Nr.current);
    var t = gn(Nt.current),
      n = di(t, e.type);
    t !== n && (ye(Cr, e), ye(Nt, n));
  }
  function po(e) {
    Cr.current === e && (we(Nt), we(Cr));
  }
  var Ee = Xt(0);
  function Nl(e) {
    for (var t = e; t !== null; ) {
      if (t.tag === 13) {
        var n = t.memoizedState;
        if (n !== null && ((n = n.dehydrated), n === null || n.data === "$?" || n.data === "$!")) return t;
      } else if (t.tag === 19 && t.memoizedProps.revealOrder !== void 0) {
        if ((t.flags & 128) !== 0) return t;
      } else if (t.child !== null) {
        ((t.child.return = t), (t = t.child));
        continue;
      }
      if (t === e) break;
      for (; t.sibling === null; ) {
        if (t.return === null || t.return === e) return null;
        t = t.return;
      }
      ((t.sibling.return = t.return), (t = t.sibling));
    }
    return null;
  }
  var ho = [];
  function mo() {
    for (var e = 0; e < ho.length; e++) ho[e]._workInProgressVersionPrimary = null;
    ho.length = 0;
  }
  var Rl = le.ReactCurrentDispatcher,
    vo = le.ReactCurrentBatchConfig,
    _n = 0,
    Ce = null,
    Oe = null,
    Ae = null,
    jl = !1,
    Rr = !1,
    jr = 0,
    Od = 0;
  function Ve() {
    throw Error(s(321));
  }
  function yo(e, t) {
    if (t === null) return !1;
    for (var n = 0; n < t.length && n < e.length; n++) if (!yt(e[n], t[n])) return !1;
    return !0;
  }
  function go(e, t, n, r, l, o) {
    if (
      ((_n = o),
      (Ce = t),
      (t.memoizedState = null),
      (t.updateQueue = null),
      (t.lanes = 0),
      (Rl.current = e === null || e.memoizedState === null ? zd : Fd),
      (e = n(r, l)),
      Rr)
    ) {
      o = 0;
      do {
        if (((Rr = !1), (jr = 0), 25 <= o)) throw Error(s(301));
        ((o += 1), (Ae = Oe = null), (t.updateQueue = null), (Rl.current = Ad), (e = n(r, l)));
      } while (Rr);
    }
    if (((Rl.current = Tl), (t = Oe !== null && Oe.next !== null), (_n = 0), (Ae = Oe = Ce = null), (jl = !1), t))
      throw Error(s(300));
    return e;
  }
  function _o() {
    var e = jr !== 0;
    return ((jr = 0), e);
  }
  function Rt() {
    var e = { memoizedState: null, baseState: null, baseQueue: null, queue: null, next: null };
    return (Ae === null ? (Ce.memoizedState = Ae = e) : (Ae = Ae.next = e), Ae);
  }
  function ft() {
    if (Oe === null) {
      var e = Ce.alternate;
      e = e !== null ? e.memoizedState : null;
    } else e = Oe.next;
    var t = Ae === null ? Ce.memoizedState : Ae.next;
    if (t !== null) ((Ae = t), (Oe = e));
    else {
      if (e === null) throw Error(s(310));
      ((Oe = e),
        (e = {
          memoizedState: Oe.memoizedState,
          baseState: Oe.baseState,
          baseQueue: Oe.baseQueue,
          queue: Oe.queue,
          next: null,
        }),
        Ae === null ? (Ce.memoizedState = Ae = e) : (Ae = Ae.next = e));
    }
    return Ae;
  }
  function Pr(e, t) {
    return typeof t == "function" ? t(e) : t;
  }
  function wo(e) {
    var t = ft(),
      n = t.queue;
    if (n === null) throw Error(s(311));
    n.lastRenderedReducer = e;
    var r = Oe,
      l = r.baseQueue,
      o = n.pending;
    if (o !== null) {
      if (l !== null) {
        var a = l.next;
        ((l.next = o.next), (o.next = a));
      }
      ((r.baseQueue = l = o), (n.pending = null));
    }
    if (l !== null) {
      ((o = l.next), (r = r.baseState));
      var v = (a = null),
        g = null,
        N = o;
      do {
        var T = N.lane;
        if ((_n & T) === T)
          (g !== null &&
            (g = g.next =
              { lane: 0, action: N.action, hasEagerState: N.hasEagerState, eagerState: N.eagerState, next: null }),
            (r = N.hasEagerState ? N.eagerState : e(r, N.action)));
        else {
          var O = { lane: T, action: N.action, hasEagerState: N.hasEagerState, eagerState: N.eagerState, next: null };
          (g === null ? ((v = g = O), (a = r)) : (g = g.next = O), (Ce.lanes |= T), (wn |= T));
        }
        N = N.next;
      } while (N !== null && N !== o);
      (g === null ? (a = r) : (g.next = v),
        yt(r, t.memoizedState) || (Ze = !0),
        (t.memoizedState = r),
        (t.baseState = a),
        (t.baseQueue = g),
        (n.lastRenderedState = r));
    }
    if (((e = n.interleaved), e !== null)) {
      l = e;
      do ((o = l.lane), (Ce.lanes |= o), (wn |= o), (l = l.next));
      while (l !== e);
    } else l === null && (n.lanes = 0);
    return [t.memoizedState, n.dispatch];
  }
  function xo(e) {
    var t = ft(),
      n = t.queue;
    if (n === null) throw Error(s(311));
    n.lastRenderedReducer = e;
    var r = n.dispatch,
      l = n.pending,
      o = t.memoizedState;
    if (l !== null) {
      n.pending = null;
      var a = (l = l.next);
      do ((o = e(o, a.action)), (a = a.next));
      while (a !== l);
      (yt(o, t.memoizedState) || (Ze = !0),
        (t.memoizedState = o),
        t.baseQueue === null && (t.baseState = o),
        (n.lastRenderedState = o));
    }
    return [o, r];
  }
  function ra() {}
  function la(e, t) {
    var n = Ce,
      r = ft(),
      l = t(),
      o = !yt(r.memoizedState, l);
    if (
      (o && ((r.memoizedState = l), (Ze = !0)),
      (r = r.queue),
      So(sa.bind(null, n, r, e), [e]),
      r.getSnapshot !== t || o || (Ae !== null && Ae.memoizedState.tag & 1))
    ) {
      if (((n.flags |= 2048), Lr(9, oa.bind(null, n, r, l, t), void 0, null), Ue === null)) throw Error(s(349));
      (_n & 30) !== 0 || ia(n, t, l);
    }
    return l;
  }
  function ia(e, t, n) {
    ((e.flags |= 16384),
      (e = { getSnapshot: t, value: n }),
      (t = Ce.updateQueue),
      t === null
        ? ((t = { lastEffect: null, stores: null }), (Ce.updateQueue = t), (t.stores = [e]))
        : ((n = t.stores), n === null ? (t.stores = [e]) : n.push(e)));
  }
  function oa(e, t, n, r) {
    ((t.value = n), (t.getSnapshot = r), ua(t) && aa(e));
  }
  function sa(e, t, n) {
    return n(function () {
      ua(t) && aa(e);
    });
  }
  function ua(e) {
    var t = e.getSnapshot;
    e = e.value;
    try {
      var n = t();
      return !yt(e, n);
    } catch {
      return !0;
    }
  }
  function aa(e) {
    var t = It(e, 1);
    t !== null && St(t, e, 1, -1);
  }
  function ca(e) {
    var t = Rt();
    return (
      typeof e == "function" && (e = e()),
      (t.memoizedState = t.baseState = e),
      (e = {
        pending: null,
        interleaved: null,
        lanes: 0,
        dispatch: null,
        lastRenderedReducer: Pr,
        lastRenderedState: e,
      }),
      (t.queue = e),
      (e = e.dispatch = Id.bind(null, Ce, e)),
      [t.memoizedState, e]
    );
  }
  function Lr(e, t, n, r) {
    return (
      (e = { tag: e, create: t, destroy: n, deps: r, next: null }),
      (t = Ce.updateQueue),
      t === null
        ? ((t = { lastEffect: null, stores: null }), (Ce.updateQueue = t), (t.lastEffect = e.next = e))
        : ((n = t.lastEffect),
          n === null ? (t.lastEffect = e.next = e) : ((r = n.next), (n.next = e), (e.next = r), (t.lastEffect = e))),
      e
    );
  }
  function fa() {
    return ft().memoizedState;
  }
  function Pl(e, t, n, r) {
    var l = Rt();
    ((Ce.flags |= e), (l.memoizedState = Lr(1 | t, n, void 0, r === void 0 ? null : r)));
  }
  function Ll(e, t, n, r) {
    var l = ft();
    r = r === void 0 ? null : r;
    var o = void 0;
    if (Oe !== null) {
      var a = Oe.memoizedState;
      if (((o = a.destroy), r !== null && yo(r, a.deps))) {
        l.memoizedState = Lr(t, n, o, r);
        return;
      }
    }
    ((Ce.flags |= e), (l.memoizedState = Lr(1 | t, n, o, r)));
  }
  function da(e, t) {
    return Pl(8390656, 8, e, t);
  }
  function So(e, t) {
    return Ll(2048, 8, e, t);
  }
  function pa(e, t) {
    return Ll(4, 2, e, t);
  }
  function ha(e, t) {
    return Ll(4, 4, e, t);
  }
  function ma(e, t) {
    if (typeof t == "function")
      return (
        (e = e()),
        t(e),
        function () {
          t(null);
        }
      );
    if (t != null)
      return (
        (e = e()),
        (t.current = e),
        function () {
          t.current = null;
        }
      );
  }
  function va(e, t, n) {
    return ((n = n != null ? n.concat([e]) : null), Ll(4, 4, ma.bind(null, t, e), n));
  }
  function ko() {}
  function ya(e, t) {
    var n = ft();
    t = t === void 0 ? null : t;
    var r = n.memoizedState;
    return r !== null && t !== null && yo(t, r[1]) ? r[0] : ((n.memoizedState = [e, t]), e);
  }
  function ga(e, t) {
    var n = ft();
    t = t === void 0 ? null : t;
    var r = n.memoizedState;
    return r !== null && t !== null && yo(t, r[1]) ? r[0] : ((e = e()), (n.memoizedState = [e, t]), e);
  }
  function _a(e, t, n) {
    return (_n & 21) === 0
      ? (e.baseState && ((e.baseState = !1), (Ze = !0)), (e.memoizedState = n))
      : (yt(n, t) || ((n = Gs()), (Ce.lanes |= n), (wn |= n), (e.baseState = !0)), t);
  }
  function Md(e, t) {
    var n = pe;
    ((pe = n !== 0 && 4 > n ? n : 4), e(!0));
    var r = vo.transition;
    vo.transition = {};
    try {
      (e(!1), t());
    } finally {
      ((pe = n), (vo.transition = r));
    }
  }
  function wa() {
    return ft().memoizedState;
  }
  function Dd(e, t, n) {
    var r = ln(e);
    if (((n = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null }), xa(e))) Sa(t, n);
    else if (((n = Zu(e, t, n, r)), n !== null)) {
      var l = Ye();
      (St(n, e, r, l), ka(n, t, r));
    }
  }
  function Id(e, t, n) {
    var r = ln(e),
      l = { lane: r, action: n, hasEagerState: !1, eagerState: null, next: null };
    if (xa(e)) Sa(t, l);
    else {
      var o = e.alternate;
      if (e.lanes === 0 && (o === null || o.lanes === 0) && ((o = t.lastRenderedReducer), o !== null))
        try {
          var a = t.lastRenderedState,
            v = o(a, n);
          if (((l.hasEagerState = !0), (l.eagerState = v), yt(v, a))) {
            var g = t.interleaved;
            (g === null ? ((l.next = l), ao(t)) : ((l.next = g.next), (g.next = l)), (t.interleaved = l));
            return;
          }
        } catch {
        } finally {
        }
      ((n = Zu(e, t, l, r)), n !== null && ((l = Ye()), St(n, e, r, l), ka(n, t, r)));
    }
  }
  function xa(e) {
    var t = e.alternate;
    return e === Ce || (t !== null && t === Ce);
  }
  function Sa(e, t) {
    Rr = jl = !0;
    var n = e.pending;
    (n === null ? (t.next = t) : ((t.next = n.next), (n.next = t)), (e.pending = t));
  }
  function ka(e, t, n) {
    if ((n & 4194240) !== 0) {
      var r = t.lanes;
      ((r &= e.pendingLanes), (n |= r), (t.lanes = n), Ei(e, n));
    }
  }
  var Tl = {
      readContext: ct,
      useCallback: Ve,
      useContext: Ve,
      useEffect: Ve,
      useImperativeHandle: Ve,
      useInsertionEffect: Ve,
      useLayoutEffect: Ve,
      useMemo: Ve,
      useReducer: Ve,
      useRef: Ve,
      useState: Ve,
      useDebugValue: Ve,
      useDeferredValue: Ve,
      useTransition: Ve,
      useMutableSource: Ve,
      useSyncExternalStore: Ve,
      useId: Ve,
      unstable_isNewReconciler: !1,
    },
    zd = {
      readContext: ct,
      useCallback: function (e, t) {
        return ((Rt().memoizedState = [e, t === void 0 ? null : t]), e);
      },
      useContext: ct,
      useEffect: da,
      useImperativeHandle: function (e, t, n) {
        return ((n = n != null ? n.concat([e]) : null), Pl(4194308, 4, ma.bind(null, t, e), n));
      },
      useLayoutEffect: function (e, t) {
        return Pl(4194308, 4, e, t);
      },
      useInsertionEffect: function (e, t) {
        return Pl(4, 2, e, t);
      },
      useMemo: function (e, t) {
        var n = Rt();
        return ((t = t === void 0 ? null : t), (e = e()), (n.memoizedState = [e, t]), e);
      },
      useReducer: function (e, t, n) {
        var r = Rt();
        return (
          (t = n !== void 0 ? n(t) : t),
          (r.memoizedState = r.baseState = t),
          (e = {
            pending: null,
            interleaved: null,
            lanes: 0,
            dispatch: null,
            lastRenderedReducer: e,
            lastRenderedState: t,
          }),
          (r.queue = e),
          (e = e.dispatch = Dd.bind(null, Ce, e)),
          [r.memoizedState, e]
        );
      },
      useRef: function (e) {
        var t = Rt();
        return ((e = { current: e }), (t.memoizedState = e));
      },
      useState: ca,
      useDebugValue: ko,
      useDeferredValue: function (e) {
        return (Rt().memoizedState = e);
      },
      useTransition: function () {
        var e = ca(!1),
          t = e[0];
        return ((e = Md.bind(null, e[1])), (Rt().memoizedState = e), [t, e]);
      },
      useMutableSource: function () {},
      useSyncExternalStore: function (e, t, n) {
        var r = Ce,
          l = Rt();
        if (ke) {
          if (n === void 0) throw Error(s(407));
          n = n();
        } else {
          if (((n = t()), Ue === null)) throw Error(s(349));
          (_n & 30) !== 0 || ia(r, t, n);
        }
        l.memoizedState = n;
        var o = { value: n, getSnapshot: t };
        return (
          (l.queue = o),
          da(sa.bind(null, r, o, e), [e]),
          (r.flags |= 2048),
          Lr(9, oa.bind(null, r, o, n, t), void 0, null),
          n
        );
      },
      useId: function () {
        var e = Rt(),
          t = Ue.identifierPrefix;
        if (ke) {
          var n = Dt,
            r = Mt;
          ((n = (r & ~(1 << (32 - vt(r) - 1))).toString(32) + n),
            (t = ":" + t + "R" + n),
            (n = jr++),
            0 < n && (t += "H" + n.toString(32)),
            (t += ":"));
        } else ((n = Od++), (t = ":" + t + "r" + n.toString(32) + ":"));
        return (e.memoizedState = t);
      },
      unstable_isNewReconciler: !1,
    },
    Fd = {
      readContext: ct,
      useCallback: ya,
      useContext: ct,
      useEffect: So,
      useImperativeHandle: va,
      useInsertionEffect: pa,
      useLayoutEffect: ha,
      useMemo: ga,
      useReducer: wo,
      useRef: fa,
      useState: function () {
        return wo(Pr);
      },
      useDebugValue: ko,
      useDeferredValue: function (e) {
        var t = ft();
        return _a(t, Oe.memoizedState, e);
      },
      useTransition: function () {
        var e = wo(Pr)[0],
          t = ft().memoizedState;
        return [e, t];
      },
      useMutableSource: ra,
      useSyncExternalStore: la,
      useId: wa,
      unstable_isNewReconciler: !1,
    },
    Ad = {
      readContext: ct,
      useCallback: ya,
      useContext: ct,
      useEffect: So,
      useImperativeHandle: va,
      useInsertionEffect: pa,
      useLayoutEffect: ha,
      useMemo: ga,
      useReducer: xo,
      useRef: fa,
      useState: function () {
        return xo(Pr);
      },
      useDebugValue: ko,
      useDeferredValue: function (e) {
        var t = ft();
        return Oe === null ? (t.memoizedState = e) : _a(t, Oe.memoizedState, e);
      },
      useTransition: function () {
        var e = xo(Pr)[0],
          t = ft().memoizedState;
        return [e, t];
      },
      useMutableSource: ra,
      useSyncExternalStore: la,
      useId: wa,
      unstable_isNewReconciler: !1,
    };
  function _t(e, t) {
    if (e && e.defaultProps) {
      ((t = H({}, t)), (e = e.defaultProps));
      for (var n in e) t[n] === void 0 && (t[n] = e[n]);
      return t;
    }
    return t;
  }
  function Eo(e, t, n, r) {
    ((t = e.memoizedState),
      (n = n(r, t)),
      (n = n == null ? t : H({}, t, n)),
      (e.memoizedState = n),
      e.lanes === 0 && (e.updateQueue.baseState = n));
  }
  var Ol = {
    isMounted: function (e) {
      return (e = e._reactInternals) ? dn(e) === e : !1;
    },
    enqueueSetState: function (e, t, n) {
      e = e._reactInternals;
      var r = Ye(),
        l = ln(e),
        o = zt(r, l);
      ((o.payload = t), n != null && (o.callback = n), (t = en(e, o, l)), t !== null && (St(t, e, l, r), El(t, e, l)));
    },
    enqueueReplaceState: function (e, t, n) {
      e = e._reactInternals;
      var r = Ye(),
        l = ln(e),
        o = zt(r, l);
      ((o.tag = 1),
        (o.payload = t),
        n != null && (o.callback = n),
        (t = en(e, o, l)),
        t !== null && (St(t, e, l, r), El(t, e, l)));
    },
    enqueueForceUpdate: function (e, t) {
      e = e._reactInternals;
      var n = Ye(),
        r = ln(e),
        l = zt(n, r);
      ((l.tag = 2), t != null && (l.callback = t), (t = en(e, l, r)), t !== null && (St(t, e, r, n), El(t, e, r)));
    },
  };
  function Ea(e, t, n, r, l, o, a) {
    return (
      (e = e.stateNode),
      typeof e.shouldComponentUpdate == "function"
        ? e.shouldComponentUpdate(r, o, a)
        : t.prototype && t.prototype.isPureReactComponent
          ? !vr(n, r) || !vr(l, o)
          : !0
    );
  }
  function Ca(e, t, n) {
    var r = !1,
      l = Jt,
      o = t.contextType;
    return (
      typeof o == "object" && o !== null
        ? (o = ct(o))
        : ((l = Je(t) ? hn : We.current), (r = t.contextTypes), (o = (r = r != null) ? Fn(e, l) : Jt)),
      (t = new t(n, o)),
      (e.memoizedState = t.state !== null && t.state !== void 0 ? t.state : null),
      (t.updater = Ol),
      (e.stateNode = t),
      (t._reactInternals = e),
      r &&
        ((e = e.stateNode),
        (e.__reactInternalMemoizedUnmaskedChildContext = l),
        (e.__reactInternalMemoizedMaskedChildContext = o)),
      t
    );
  }
  function Na(e, t, n, r) {
    ((e = t.state),
      typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r),
      typeof t.UNSAFE_componentWillReceiveProps == "function" && t.UNSAFE_componentWillReceiveProps(n, r),
      t.state !== e && Ol.enqueueReplaceState(t, t.state, null));
  }
  function Co(e, t, n, r) {
    var l = e.stateNode;
    ((l.props = n), (l.state = e.memoizedState), (l.refs = {}), co(e));
    var o = t.contextType;
    (typeof o == "object" && o !== null ? (l.context = ct(o)) : ((o = Je(t) ? hn : We.current), (l.context = Fn(e, o))),
      (l.state = e.memoizedState),
      (o = t.getDerivedStateFromProps),
      typeof o == "function" && (Eo(e, t, o, n), (l.state = e.memoizedState)),
      typeof t.getDerivedStateFromProps == "function" ||
        typeof l.getSnapshotBeforeUpdate == "function" ||
        (typeof l.UNSAFE_componentWillMount != "function" && typeof l.componentWillMount != "function") ||
        ((t = l.state),
        typeof l.componentWillMount == "function" && l.componentWillMount(),
        typeof l.UNSAFE_componentWillMount == "function" && l.UNSAFE_componentWillMount(),
        t !== l.state && Ol.enqueueReplaceState(l, l.state, null),
        Cl(e, n, l, r),
        (l.state = e.memoizedState)),
      typeof l.componentDidMount == "function" && (e.flags |= 4194308));
  }
  function Qn(e, t) {
    try {
      var n = "",
        r = t;
      do ((n += ue(r)), (r = r.return));
      while (r);
      var l = n;
    } catch (o) {
      l =
        `
Error generating stack: ` +
        o.message +
        `
` +
        o.stack;
    }
    return { value: e, source: t, stack: l, digest: null };
  }
  function No(e, t, n) {
    return { value: e, source: null, stack: n ?? null, digest: t ?? null };
  }
  function Ro(e, t) {
    try {
      console.error(t.value);
    } catch (n) {
      setTimeout(function () {
        throw n;
      });
    }
  }
  var Ud = typeof WeakMap == "function" ? WeakMap : Map;
  function Ra(e, t, n) {
    ((n = zt(-1, n)), (n.tag = 3), (n.payload = { element: null }));
    var r = t.value;
    return (
      (n.callback = function () {
        (Ul || ((Ul = !0), (Ho = r)), Ro(e, t));
      }),
      n
    );
  }
  function ja(e, t, n) {
    ((n = zt(-1, n)), (n.tag = 3));
    var r = e.type.getDerivedStateFromError;
    if (typeof r == "function") {
      var l = t.value;
      ((n.payload = function () {
        return r(l);
      }),
        (n.callback = function () {
          Ro(e, t);
        }));
    }
    var o = e.stateNode;
    return (
      o !== null &&
        typeof o.componentDidCatch == "function" &&
        (n.callback = function () {
          (Ro(e, t), typeof r != "function" && (nn === null ? (nn = new Set([this])) : nn.add(this)));
          var a = t.stack;
          this.componentDidCatch(t.value, { componentStack: a !== null ? a : "" });
        }),
      n
    );
  }
  function Pa(e, t, n) {
    var r = e.pingCache;
    if (r === null) {
      r = e.pingCache = new Ud();
      var l = new Set();
      r.set(t, l);
    } else ((l = r.get(t)), l === void 0 && ((l = new Set()), r.set(t, l)));
    l.has(n) || (l.add(n), (e = bd.bind(null, e, t, n)), t.then(e, e));
  }
  function La(e) {
    do {
      var t;
      if (((t = e.tag === 13) && ((t = e.memoizedState), (t = t !== null ? t.dehydrated !== null : !0)), t)) return e;
      e = e.return;
    } while (e !== null);
    return null;
  }
  function Ta(e, t, n, r, l) {
    return (e.mode & 1) === 0
      ? (e === t
          ? (e.flags |= 65536)
          : ((e.flags |= 128),
            (n.flags |= 131072),
            (n.flags &= -52805),
            n.tag === 1 && (n.alternate === null ? (n.tag = 17) : ((t = zt(-1, 1)), (t.tag = 2), en(n, t, 1))),
            (n.lanes |= 1)),
        e)
      : ((e.flags |= 65536), (e.lanes = l), e);
  }
  var $d = le.ReactCurrentOwner,
    Ze = !1;
  function qe(e, t, n, r) {
    t.child = e === null ? Ju(t, null, n, r) : Bn(t, e.child, n, r);
  }
  function Oa(e, t, n, r, l) {
    n = n.render;
    var o = t.ref;
    return (
      Wn(t, l),
      (r = go(e, t, n, r, o, l)),
      (n = _o()),
      e !== null && !Ze
        ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~l), Ft(e, t, l))
        : (ke && n && eo(t), (t.flags |= 1), qe(e, t, r, l), t.child)
    );
  }
  function Ma(e, t, n, r, l) {
    if (e === null) {
      var o = n.type;
      return typeof o == "function" &&
        !Go(o) &&
        o.defaultProps === void 0 &&
        n.compare === null &&
        n.defaultProps === void 0
        ? ((t.tag = 15), (t.type = o), Da(e, t, o, r, l))
        : ((e = Ql(n.type, null, r, t, t.mode, l)), (e.ref = t.ref), (e.return = t), (t.child = e));
    }
    if (((o = e.child), (e.lanes & l) === 0)) {
      var a = o.memoizedProps;
      if (((n = n.compare), (n = n !== null ? n : vr), n(a, r) && e.ref === t.ref)) return Ft(e, t, l);
    }
    return ((t.flags |= 1), (e = sn(o, r)), (e.ref = t.ref), (e.return = t), (t.child = e));
  }
  function Da(e, t, n, r, l) {
    if (e !== null) {
      var o = e.memoizedProps;
      if (vr(o, r) && e.ref === t.ref)
        if (((Ze = !1), (t.pendingProps = r = o), (e.lanes & l) !== 0)) (e.flags & 131072) !== 0 && (Ze = !0);
        else return ((t.lanes = e.lanes), Ft(e, t, l));
    }
    return jo(e, t, n, r, l);
  }
  function Ia(e, t, n) {
    var r = t.pendingProps,
      l = r.children,
      o = e !== null ? e.memoizedState : null;
    if (r.mode === "hidden")
      if ((t.mode & 1) === 0)
        ((t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }), ye(qn, ot), (ot |= n));
      else {
        if ((n & 1073741824) === 0)
          return (
            (e = o !== null ? o.baseLanes | n : n),
            (t.lanes = t.childLanes = 1073741824),
            (t.memoizedState = { baseLanes: e, cachePool: null, transitions: null }),
            (t.updateQueue = null),
            ye(qn, ot),
            (ot |= e),
            null
          );
        ((t.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }),
          (r = o !== null ? o.baseLanes : n),
          ye(qn, ot),
          (ot |= r));
      }
    else (o !== null ? ((r = o.baseLanes | n), (t.memoizedState = null)) : (r = n), ye(qn, ot), (ot |= r));
    return (qe(e, t, l, n), t.child);
  }
  function za(e, t) {
    var n = t.ref;
    ((e === null && n !== null) || (e !== null && e.ref !== n)) && ((t.flags |= 512), (t.flags |= 2097152));
  }
  function jo(e, t, n, r, l) {
    var o = Je(n) ? hn : We.current;
    return (
      (o = Fn(t, o)),
      Wn(t, l),
      (n = go(e, t, n, r, o, l)),
      (r = _o()),
      e !== null && !Ze
        ? ((t.updateQueue = e.updateQueue), (t.flags &= -2053), (e.lanes &= ~l), Ft(e, t, l))
        : (ke && r && eo(t), (t.flags |= 1), qe(e, t, n, l), t.child)
    );
  }
  function Fa(e, t, n, r, l) {
    if (Je(n)) {
      var o = !0;
      vl(t);
    } else o = !1;
    if ((Wn(t, l), t.stateNode === null)) (Dl(e, t), Ca(t, n, r), Co(t, n, r, l), (r = !0));
    else if (e === null) {
      var a = t.stateNode,
        v = t.memoizedProps;
      a.props = v;
      var g = a.context,
        N = n.contextType;
      typeof N == "object" && N !== null ? (N = ct(N)) : ((N = Je(n) ? hn : We.current), (N = Fn(t, N)));
      var T = n.getDerivedStateFromProps,
        O = typeof T == "function" || typeof a.getSnapshotBeforeUpdate == "function";
      (O ||
        (typeof a.UNSAFE_componentWillReceiveProps != "function" && typeof a.componentWillReceiveProps != "function") ||
        ((v !== r || g !== N) && Na(t, a, r, N)),
        (bt = !1));
      var P = t.memoizedState;
      ((a.state = P),
        Cl(t, r, a, l),
        (g = t.memoizedState),
        v !== r || P !== g || Xe.current || bt
          ? (typeof T == "function" && (Eo(t, n, T, r), (g = t.memoizedState)),
            (v = bt || Ea(t, n, v, r, P, g, N))
              ? (O ||
                  (typeof a.UNSAFE_componentWillMount != "function" && typeof a.componentWillMount != "function") ||
                  (typeof a.componentWillMount == "function" && a.componentWillMount(),
                  typeof a.UNSAFE_componentWillMount == "function" && a.UNSAFE_componentWillMount()),
                typeof a.componentDidMount == "function" && (t.flags |= 4194308))
              : (typeof a.componentDidMount == "function" && (t.flags |= 4194308),
                (t.memoizedProps = r),
                (t.memoizedState = g)),
            (a.props = r),
            (a.state = g),
            (a.context = N),
            (r = v))
          : (typeof a.componentDidMount == "function" && (t.flags |= 4194308), (r = !1)));
    } else {
      ((a = t.stateNode),
        bu(e, t),
        (v = t.memoizedProps),
        (N = t.type === t.elementType ? v : _t(t.type, v)),
        (a.props = N),
        (O = t.pendingProps),
        (P = a.context),
        (g = n.contextType),
        typeof g == "object" && g !== null ? (g = ct(g)) : ((g = Je(n) ? hn : We.current), (g = Fn(t, g))));
      var B = n.getDerivedStateFromProps;
      ((T = typeof B == "function" || typeof a.getSnapshotBeforeUpdate == "function") ||
        (typeof a.UNSAFE_componentWillReceiveProps != "function" && typeof a.componentWillReceiveProps != "function") ||
        ((v !== O || P !== g) && Na(t, a, r, g)),
        (bt = !1),
        (P = t.memoizedState),
        (a.state = P),
        Cl(t, r, a, l));
      var Q = t.memoizedState;
      v !== O || P !== Q || Xe.current || bt
        ? (typeof B == "function" && (Eo(t, n, B, r), (Q = t.memoizedState)),
          (N = bt || Ea(t, n, N, r, P, Q, g) || !1)
            ? (T ||
                (typeof a.UNSAFE_componentWillUpdate != "function" && typeof a.componentWillUpdate != "function") ||
                (typeof a.componentWillUpdate == "function" && a.componentWillUpdate(r, Q, g),
                typeof a.UNSAFE_componentWillUpdate == "function" && a.UNSAFE_componentWillUpdate(r, Q, g)),
              typeof a.componentDidUpdate == "function" && (t.flags |= 4),
              typeof a.getSnapshotBeforeUpdate == "function" && (t.flags |= 1024))
            : (typeof a.componentDidUpdate != "function" ||
                (v === e.memoizedProps && P === e.memoizedState) ||
                (t.flags |= 4),
              typeof a.getSnapshotBeforeUpdate != "function" ||
                (v === e.memoizedProps && P === e.memoizedState) ||
                (t.flags |= 1024),
              (t.memoizedProps = r),
              (t.memoizedState = Q)),
          (a.props = r),
          (a.state = Q),
          (a.context = g),
          (r = N))
        : (typeof a.componentDidUpdate != "function" ||
            (v === e.memoizedProps && P === e.memoizedState) ||
            (t.flags |= 4),
          typeof a.getSnapshotBeforeUpdate != "function" ||
            (v === e.memoizedProps && P === e.memoizedState) ||
            (t.flags |= 1024),
          (r = !1));
    }
    return Po(e, t, n, r, o, l);
  }
  function Po(e, t, n, r, l, o) {
    za(e, t);
    var a = (t.flags & 128) !== 0;
    if (!r && !a) return (l && Hu(t, n, !1), Ft(e, t, o));
    ((r = t.stateNode), ($d.current = t));
    var v = a && typeof n.getDerivedStateFromError != "function" ? null : r.render();
    return (
      (t.flags |= 1),
      e !== null && a ? ((t.child = Bn(t, e.child, null, o)), (t.child = Bn(t, null, v, o))) : qe(e, t, v, o),
      (t.memoizedState = r.state),
      l && Hu(t, n, !0),
      t.child
    );
  }
  function Aa(e) {
    var t = e.stateNode;
    (t.pendingContext ? $u(e, t.pendingContext, t.pendingContext !== t.context) : t.context && $u(e, t.context, !1),
      fo(e, t.containerInfo));
  }
  function Ua(e, t, n, r, l) {
    return ($n(), lo(l), (t.flags |= 256), qe(e, t, n, r), t.child);
  }
  var Lo = { dehydrated: null, treeContext: null, retryLane: 0 };
  function To(e) {
    return { baseLanes: e, cachePool: null, transitions: null };
  }
  function $a(e, t, n) {
    var r = t.pendingProps,
      l = Ee.current,
      o = !1,
      a = (t.flags & 128) !== 0,
      v;
    if (
      ((v = a) || (v = e !== null && e.memoizedState === null ? !1 : (l & 2) !== 0),
      v ? ((o = !0), (t.flags &= -129)) : (e === null || e.memoizedState !== null) && (l |= 1),
      ye(Ee, l & 1),
      e === null)
    )
      return (
        ro(t),
        (e = t.memoizedState),
        e !== null && ((e = e.dehydrated), e !== null)
          ? ((t.mode & 1) === 0 ? (t.lanes = 1) : e.data === "$!" ? (t.lanes = 8) : (t.lanes = 1073741824), null)
          : ((a = r.children),
            (e = r.fallback),
            o
              ? ((r = t.mode),
                (o = t.child),
                (a = { mode: "hidden", children: a }),
                (r & 1) === 0 && o !== null ? ((o.childLanes = 0), (o.pendingProps = a)) : (o = Kl(a, r, 0, null)),
                (e = En(e, r, n, null)),
                (o.return = t),
                (e.return = t),
                (o.sibling = e),
                (t.child = o),
                (t.child.memoizedState = To(n)),
                (t.memoizedState = Lo),
                e)
              : Oo(t, a))
      );
    if (((l = e.memoizedState), l !== null && ((v = l.dehydrated), v !== null))) return Bd(e, t, a, r, v, l, n);
    if (o) {
      ((o = r.fallback), (a = t.mode), (l = e.child), (v = l.sibling));
      var g = { mode: "hidden", children: r.children };
      return (
        (a & 1) === 0 && t.child !== l
          ? ((r = t.child), (r.childLanes = 0), (r.pendingProps = g), (t.deletions = null))
          : ((r = sn(l, g)), (r.subtreeFlags = l.subtreeFlags & 14680064)),
        v !== null ? (o = sn(v, o)) : ((o = En(o, a, n, null)), (o.flags |= 2)),
        (o.return = t),
        (r.return = t),
        (r.sibling = o),
        (t.child = r),
        (r = o),
        (o = t.child),
        (a = e.child.memoizedState),
        (a = a === null ? To(n) : { baseLanes: a.baseLanes | n, cachePool: null, transitions: a.transitions }),
        (o.memoizedState = a),
        (o.childLanes = e.childLanes & ~n),
        (t.memoizedState = Lo),
        r
      );
    }
    return (
      (o = e.child),
      (e = o.sibling),
      (r = sn(o, { mode: "visible", children: r.children })),
      (t.mode & 1) === 0 && (r.lanes = n),
      (r.return = t),
      (r.sibling = null),
      e !== null && ((n = t.deletions), n === null ? ((t.deletions = [e]), (t.flags |= 16)) : n.push(e)),
      (t.child = r),
      (t.memoizedState = null),
      r
    );
  }
  function Oo(e, t) {
    return ((t = Kl({ mode: "visible", children: t }, e.mode, 0, null)), (t.return = e), (e.child = t));
  }
  function Ml(e, t, n, r) {
    return (
      r !== null && lo(r),
      Bn(t, e.child, null, n),
      (e = Oo(t, t.pendingProps.children)),
      (e.flags |= 2),
      (t.memoizedState = null),
      e
    );
  }
  function Bd(e, t, n, r, l, o, a) {
    if (n)
      return t.flags & 256
        ? ((t.flags &= -257), (r = No(Error(s(422)))), Ml(e, t, a, r))
        : t.memoizedState !== null
          ? ((t.child = e.child), (t.flags |= 128), null)
          : ((o = r.fallback),
            (l = t.mode),
            (r = Kl({ mode: "visible", children: r.children }, l, 0, null)),
            (o = En(o, l, a, null)),
            (o.flags |= 2),
            (r.return = t),
            (o.return = t),
            (r.sibling = o),
            (t.child = r),
            (t.mode & 1) !== 0 && Bn(t, e.child, null, a),
            (t.child.memoizedState = To(a)),
            (t.memoizedState = Lo),
            o);
    if ((t.mode & 1) === 0) return Ml(e, t, a, null);
    if (l.data === "$!") {
      if (((r = l.nextSibling && l.nextSibling.dataset), r)) var v = r.dgst;
      return ((r = v), (o = Error(s(419))), (r = No(o, r, void 0)), Ml(e, t, a, r));
    }
    if (((v = (a & e.childLanes) !== 0), Ze || v)) {
      if (((r = Ue), r !== null)) {
        switch (a & -a) {
          case 4:
            l = 2;
            break;
          case 16:
            l = 8;
            break;
          case 64:
          case 128:
          case 256:
          case 512:
          case 1024:
          case 2048:
          case 4096:
          case 8192:
          case 16384:
          case 32768:
          case 65536:
          case 131072:
          case 262144:
          case 524288:
          case 1048576:
          case 2097152:
          case 4194304:
          case 8388608:
          case 16777216:
          case 33554432:
          case 67108864:
            l = 32;
            break;
          case 536870912:
            l = 268435456;
            break;
          default:
            l = 0;
        }
        ((l = (l & (r.suspendedLanes | a)) !== 0 ? 0 : l),
          l !== 0 && l !== o.retryLane && ((o.retryLane = l), It(e, l), St(r, e, l, -1)));
      }
      return (Yo(), (r = No(Error(s(421)))), Ml(e, t, a, r));
    }
    return l.data === "$?"
      ? ((t.flags |= 128), (t.child = e.child), (t = ep.bind(null, e)), (l._reactRetry = t), null)
      : ((e = o.treeContext),
        (it = Gt(l.nextSibling)),
        (lt = t),
        (ke = !0),
        (gt = null),
        e !== null && ((ut[at++] = Mt), (ut[at++] = Dt), (ut[at++] = mn), (Mt = e.id), (Dt = e.overflow), (mn = t)),
        (t = Oo(t, r.children)),
        (t.flags |= 4096),
        t);
  }
  function Ba(e, t, n) {
    e.lanes |= t;
    var r = e.alternate;
    (r !== null && (r.lanes |= t), uo(e.return, t, n));
  }
  function Mo(e, t, n, r, l) {
    var o = e.memoizedState;
    o === null
      ? (e.memoizedState = { isBackwards: t, rendering: null, renderingStartTime: 0, last: r, tail: n, tailMode: l })
      : ((o.isBackwards = t),
        (o.rendering = null),
        (o.renderingStartTime = 0),
        (o.last = r),
        (o.tail = n),
        (o.tailMode = l));
  }
  function Ha(e, t, n) {
    var r = t.pendingProps,
      l = r.revealOrder,
      o = r.tail;
    if ((qe(e, t, r.children, n), (r = Ee.current), (r & 2) !== 0)) ((r = (r & 1) | 2), (t.flags |= 128));
    else {
      if (e !== null && (e.flags & 128) !== 0)
        e: for (e = t.child; e !== null; ) {
          if (e.tag === 13) e.memoizedState !== null && Ba(e, n, t);
          else if (e.tag === 19) Ba(e, n, t);
          else if (e.child !== null) {
            ((e.child.return = e), (e = e.child));
            continue;
          }
          if (e === t) break e;
          for (; e.sibling === null; ) {
            if (e.return === null || e.return === t) break e;
            e = e.return;
          }
          ((e.sibling.return = e.return), (e = e.sibling));
        }
      r &= 1;
    }
    if ((ye(Ee, r), (t.mode & 1) === 0)) t.memoizedState = null;
    else
      switch (l) {
        case "forwards":
          for (n = t.child, l = null; n !== null; )
            ((e = n.alternate), e !== null && Nl(e) === null && (l = n), (n = n.sibling));
          ((n = l),
            n === null ? ((l = t.child), (t.child = null)) : ((l = n.sibling), (n.sibling = null)),
            Mo(t, !1, l, n, o));
          break;
        case "backwards":
          for (n = null, l = t.child, t.child = null; l !== null; ) {
            if (((e = l.alternate), e !== null && Nl(e) === null)) {
              t.child = l;
              break;
            }
            ((e = l.sibling), (l.sibling = n), (n = l), (l = e));
          }
          Mo(t, !0, n, null, o);
          break;
        case "together":
          Mo(t, !1, null, null, void 0);
          break;
        default:
          t.memoizedState = null;
      }
    return t.child;
  }
  function Dl(e, t) {
    (t.mode & 1) === 0 && e !== null && ((e.alternate = null), (t.alternate = null), (t.flags |= 2));
  }
  function Ft(e, t, n) {
    if ((e !== null && (t.dependencies = e.dependencies), (wn |= t.lanes), (n & t.childLanes) === 0)) return null;
    if (e !== null && t.child !== e.child) throw Error(s(153));
    if (t.child !== null) {
      for (e = t.child, n = sn(e, e.pendingProps), t.child = n, n.return = t; e.sibling !== null; )
        ((e = e.sibling), (n = n.sibling = sn(e, e.pendingProps)), (n.return = t));
      n.sibling = null;
    }
    return t.child;
  }
  function Hd(e, t, n) {
    switch (t.tag) {
      case 3:
        (Aa(t), $n());
        break;
      case 5:
        na(t);
        break;
      case 1:
        Je(t.type) && vl(t);
        break;
      case 4:
        fo(t, t.stateNode.containerInfo);
        break;
      case 10:
        var r = t.type._context,
          l = t.memoizedProps.value;
        (ye(Sl, r._currentValue), (r._currentValue = l));
        break;
      case 13:
        if (((r = t.memoizedState), r !== null))
          return r.dehydrated !== null
            ? (ye(Ee, Ee.current & 1), (t.flags |= 128), null)
            : (n & t.child.childLanes) !== 0
              ? $a(e, t, n)
              : (ye(Ee, Ee.current & 1), (e = Ft(e, t, n)), e !== null ? e.sibling : null);
        ye(Ee, Ee.current & 1);
        break;
      case 19:
        if (((r = (n & t.childLanes) !== 0), (e.flags & 128) !== 0)) {
          if (r) return Ha(e, t, n);
          t.flags |= 128;
        }
        if (
          ((l = t.memoizedState),
          l !== null && ((l.rendering = null), (l.tail = null), (l.lastEffect = null)),
          ye(Ee, Ee.current),
          r)
        )
          break;
        return null;
      case 22:
      case 23:
        return ((t.lanes = 0), Ia(e, t, n));
    }
    return Ft(e, t, n);
  }
  var Wa, Do, Va, Qa;
  ((Wa = function (e, t) {
    for (var n = t.child; n !== null; ) {
      if (n.tag === 5 || n.tag === 6) e.appendChild(n.stateNode);
      else if (n.tag !== 4 && n.child !== null) {
        ((n.child.return = n), (n = n.child));
        continue;
      }
      if (n === t) break;
      for (; n.sibling === null; ) {
        if (n.return === null || n.return === t) return;
        n = n.return;
      }
      ((n.sibling.return = n.return), (n = n.sibling));
    }
  }),
    (Do = function () {}),
    (Va = function (e, t, n, r) {
      var l = e.memoizedProps;
      if (l !== r) {
        ((e = t.stateNode), gn(Nt.current));
        var o = null;
        switch (n) {
          case "input":
            ((l = ui(e, l)), (r = ui(e, r)), (o = []));
            break;
          case "select":
            ((l = H({}, l, { value: void 0 })), (r = H({}, r, { value: void 0 })), (o = []));
            break;
          case "textarea":
            ((l = fi(e, l)), (r = fi(e, r)), (o = []));
            break;
          default:
            typeof l.onClick != "function" && typeof r.onClick == "function" && (e.onclick = pl);
        }
        pi(n, r);
        var a;
        n = null;
        for (N in l)
          if (!r.hasOwnProperty(N) && l.hasOwnProperty(N) && l[N] != null)
            if (N === "style") {
              var v = l[N];
              for (a in v) v.hasOwnProperty(a) && (n || (n = {}), (n[a] = ""));
            } else
              N !== "dangerouslySetInnerHTML" &&
                N !== "children" &&
                N !== "suppressContentEditableWarning" &&
                N !== "suppressHydrationWarning" &&
                N !== "autoFocus" &&
                (f.hasOwnProperty(N) ? o || (o = []) : (o = o || []).push(N, null));
        for (N in r) {
          var g = r[N];
          if (((v = l != null ? l[N] : void 0), r.hasOwnProperty(N) && g !== v && (g != null || v != null)))
            if (N === "style")
              if (v) {
                for (a in v) !v.hasOwnProperty(a) || (g && g.hasOwnProperty(a)) || (n || (n = {}), (n[a] = ""));
                for (a in g) g.hasOwnProperty(a) && v[a] !== g[a] && (n || (n = {}), (n[a] = g[a]));
              } else (n || (o || (o = []), o.push(N, n)), (n = g));
            else
              N === "dangerouslySetInnerHTML"
                ? ((g = g ? g.__html : void 0),
                  (v = v ? v.__html : void 0),
                  g != null && v !== g && (o = o || []).push(N, g))
                : N === "children"
                  ? (typeof g != "string" && typeof g != "number") || (o = o || []).push(N, "" + g)
                  : N !== "suppressContentEditableWarning" &&
                    N !== "suppressHydrationWarning" &&
                    (f.hasOwnProperty(N)
                      ? (g != null && N === "onScroll" && _e("scroll", e), o || v === g || (o = []))
                      : (o = o || []).push(N, g));
        }
        n && (o = o || []).push("style", n);
        var N = o;
        (t.updateQueue = N) && (t.flags |= 4);
      }
    }),
    (Qa = function (e, t, n, r) {
      n !== r && (t.flags |= 4);
    }));
  function Tr(e, t) {
    if (!ke)
      switch (e.tailMode) {
        case "hidden":
          t = e.tail;
          for (var n = null; t !== null; ) (t.alternate !== null && (n = t), (t = t.sibling));
          n === null ? (e.tail = null) : (n.sibling = null);
          break;
        case "collapsed":
          n = e.tail;
          for (var r = null; n !== null; ) (n.alternate !== null && (r = n), (n = n.sibling));
          r === null ? (t || e.tail === null ? (e.tail = null) : (e.tail.sibling = null)) : (r.sibling = null);
      }
  }
  function Qe(e) {
    var t = e.alternate !== null && e.alternate.child === e.child,
      n = 0,
      r = 0;
    if (t)
      for (var l = e.child; l !== null; )
        ((n |= l.lanes | l.childLanes),
          (r |= l.subtreeFlags & 14680064),
          (r |= l.flags & 14680064),
          (l.return = e),
          (l = l.sibling));
    else
      for (l = e.child; l !== null; )
        ((n |= l.lanes | l.childLanes), (r |= l.subtreeFlags), (r |= l.flags), (l.return = e), (l = l.sibling));
    return ((e.subtreeFlags |= r), (e.childLanes = n), t);
  }
  function Wd(e, t, n) {
    var r = t.pendingProps;
    switch ((to(t), t.tag)) {
      case 2:
      case 16:
      case 15:
      case 0:
      case 11:
      case 7:
      case 8:
      case 12:
      case 9:
      case 14:
        return (Qe(t), null);
      case 1:
        return (Je(t.type) && ml(), Qe(t), null);
      case 3:
        return (
          (r = t.stateNode),
          Vn(),
          we(Xe),
          we(We),
          mo(),
          r.pendingContext && ((r.context = r.pendingContext), (r.pendingContext = null)),
          (e === null || e.child === null) &&
            (wl(t)
              ? (t.flags |= 4)
              : e === null ||
                (e.memoizedState.isDehydrated && (t.flags & 256) === 0) ||
                ((t.flags |= 1024), gt !== null && (Qo(gt), (gt = null)))),
          Do(e, t),
          Qe(t),
          null
        );
      case 5:
        po(t);
        var l = gn(Nr.current);
        if (((n = t.type), e !== null && t.stateNode != null))
          (Va(e, t, n, r, l), e.ref !== t.ref && ((t.flags |= 512), (t.flags |= 2097152)));
        else {
          if (!r) {
            if (t.stateNode === null) throw Error(s(166));
            return (Qe(t), null);
          }
          if (((e = gn(Nt.current)), wl(t))) {
            ((r = t.stateNode), (n = t.type));
            var o = t.memoizedProps;
            switch (((r[Ct] = t), (r[xr] = o), (e = (t.mode & 1) !== 0), n)) {
              case "dialog":
                (_e("cancel", r), _e("close", r));
                break;
              case "iframe":
              case "object":
              case "embed":
                _e("load", r);
                break;
              case "video":
              case "audio":
                for (l = 0; l < gr.length; l++) _e(gr[l], r);
                break;
              case "source":
                _e("error", r);
                break;
              case "img":
              case "image":
              case "link":
                (_e("error", r), _e("load", r));
                break;
              case "details":
                _e("toggle", r);
                break;
              case "input":
                (Cs(r, o), _e("invalid", r));
                break;
              case "select":
                ((r._wrapperState = { wasMultiple: !!o.multiple }), _e("invalid", r));
                break;
              case "textarea":
                (js(r, o), _e("invalid", r));
            }
            (pi(n, o), (l = null));
            for (var a in o)
              if (o.hasOwnProperty(a)) {
                var v = o[a];
                a === "children"
                  ? typeof v == "string"
                    ? r.textContent !== v &&
                      (o.suppressHydrationWarning !== !0 && dl(r.textContent, v, e), (l = ["children", v]))
                    : typeof v == "number" &&
                      r.textContent !== "" + v &&
                      (o.suppressHydrationWarning !== !0 && dl(r.textContent, v, e), (l = ["children", "" + v]))
                  : f.hasOwnProperty(a) && v != null && a === "onScroll" && _e("scroll", r);
              }
            switch (n) {
              case "input":
                (Wr(r), Rs(r, o, !0));
                break;
              case "textarea":
                (Wr(r), Ls(r));
                break;
              case "select":
              case "option":
                break;
              default:
                typeof o.onClick == "function" && (r.onclick = pl);
            }
            ((r = l), (t.updateQueue = r), r !== null && (t.flags |= 4));
          } else {
            ((a = l.nodeType === 9 ? l : l.ownerDocument),
              e === "http://www.w3.org/1999/xhtml" && (e = Ts(n)),
              e === "http://www.w3.org/1999/xhtml"
                ? n === "script"
                  ? ((e = a.createElement("div")),
                    (e.innerHTML = "<script><\/script>"),
                    (e = e.removeChild(e.firstChild)))
                  : typeof r.is == "string"
                    ? (e = a.createElement(n, { is: r.is }))
                    : ((e = a.createElement(n)),
                      n === "select" && ((a = e), r.multiple ? (a.multiple = !0) : r.size && (a.size = r.size)))
                : (e = a.createElementNS(e, n)),
              (e[Ct] = t),
              (e[xr] = r),
              Wa(e, t, !1, !1),
              (t.stateNode = e));
            e: {
              switch (((a = hi(n, r)), n)) {
                case "dialog":
                  (_e("cancel", e), _e("close", e), (l = r));
                  break;
                case "iframe":
                case "object":
                case "embed":
                  (_e("load", e), (l = r));
                  break;
                case "video":
                case "audio":
                  for (l = 0; l < gr.length; l++) _e(gr[l], e);
                  l = r;
                  break;
                case "source":
                  (_e("error", e), (l = r));
                  break;
                case "img":
                case "image":
                case "link":
                  (_e("error", e), _e("load", e), (l = r));
                  break;
                case "details":
                  (_e("toggle", e), (l = r));
                  break;
                case "input":
                  (Cs(e, r), (l = ui(e, r)), _e("invalid", e));
                  break;
                case "option":
                  l = r;
                  break;
                case "select":
                  ((e._wrapperState = { wasMultiple: !!r.multiple }),
                    (l = H({}, r, { value: void 0 })),
                    _e("invalid", e));
                  break;
                case "textarea":
                  (js(e, r), (l = fi(e, r)), _e("invalid", e));
                  break;
                default:
                  l = r;
              }
              (pi(n, l), (v = l));
              for (o in v)
                if (v.hasOwnProperty(o)) {
                  var g = v[o];
                  o === "style"
                    ? Ds(e, g)
                    : o === "dangerouslySetInnerHTML"
                      ? ((g = g ? g.__html : void 0), g != null && Os(e, g))
                      : o === "children"
                        ? typeof g == "string"
                          ? (n !== "textarea" || g !== "") && bn(e, g)
                          : typeof g == "number" && bn(e, "" + g)
                        : o !== "suppressContentEditableWarning" &&
                          o !== "suppressHydrationWarning" &&
                          o !== "autoFocus" &&
                          (f.hasOwnProperty(o)
                            ? g != null && o === "onScroll" && _e("scroll", e)
                            : g != null && A(e, o, g, a));
                }
              switch (n) {
                case "input":
                  (Wr(e), Rs(e, r, !1));
                  break;
                case "textarea":
                  (Wr(e), Ls(e));
                  break;
                case "option":
                  r.value != null && e.setAttribute("value", "" + de(r.value));
                  break;
                case "select":
                  ((e.multiple = !!r.multiple),
                    (o = r.value),
                    o != null
                      ? Cn(e, !!r.multiple, o, !1)
                      : r.defaultValue != null && Cn(e, !!r.multiple, r.defaultValue, !0));
                  break;
                default:
                  typeof l.onClick == "function" && (e.onclick = pl);
              }
              switch (n) {
                case "button":
                case "input":
                case "select":
                case "textarea":
                  r = !!r.autoFocus;
                  break e;
                case "img":
                  r = !0;
                  break e;
                default:
                  r = !1;
              }
            }
            r && (t.flags |= 4);
          }
          t.ref !== null && ((t.flags |= 512), (t.flags |= 2097152));
        }
        return (Qe(t), null);
      case 6:
        if (e && t.stateNode != null) Qa(e, t, e.memoizedProps, r);
        else {
          if (typeof r != "string" && t.stateNode === null) throw Error(s(166));
          if (((n = gn(Nr.current)), gn(Nt.current), wl(t))) {
            if (
              ((r = t.stateNode), (n = t.memoizedProps), (r[Ct] = t), (o = r.nodeValue !== n) && ((e = lt), e !== null))
            )
              switch (e.tag) {
                case 3:
                  dl(r.nodeValue, n, (e.mode & 1) !== 0);
                  break;
                case 5:
                  e.memoizedProps.suppressHydrationWarning !== !0 && dl(r.nodeValue, n, (e.mode & 1) !== 0);
              }
            o && (t.flags |= 4);
          } else ((r = (n.nodeType === 9 ? n : n.ownerDocument).createTextNode(r)), (r[Ct] = t), (t.stateNode = r));
        }
        return (Qe(t), null);
      case 13:
        if (
          (we(Ee),
          (r = t.memoizedState),
          e === null || (e.memoizedState !== null && e.memoizedState.dehydrated !== null))
        ) {
          if (ke && it !== null && (t.mode & 1) !== 0 && (t.flags & 128) === 0)
            (Yu(), $n(), (t.flags |= 98560), (o = !1));
          else if (((o = wl(t)), r !== null && r.dehydrated !== null)) {
            if (e === null) {
              if (!o) throw Error(s(318));
              if (((o = t.memoizedState), (o = o !== null ? o.dehydrated : null), !o)) throw Error(s(317));
              o[Ct] = t;
            } else ($n(), (t.flags & 128) === 0 && (t.memoizedState = null), (t.flags |= 4));
            (Qe(t), (o = !1));
          } else (gt !== null && (Qo(gt), (gt = null)), (o = !0));
          if (!o) return t.flags & 65536 ? t : null;
        }
        return (t.flags & 128) !== 0
          ? ((t.lanes = n), t)
          : ((r = r !== null),
            r !== (e !== null && e.memoizedState !== null) &&
              r &&
              ((t.child.flags |= 8192),
              (t.mode & 1) !== 0 && (e === null || (Ee.current & 1) !== 0 ? Me === 0 && (Me = 3) : Yo())),
            t.updateQueue !== null && (t.flags |= 4),
            Qe(t),
            null);
      case 4:
        return (Vn(), Do(e, t), e === null && _r(t.stateNode.containerInfo), Qe(t), null);
      case 10:
        return (so(t.type._context), Qe(t), null);
      case 17:
        return (Je(t.type) && ml(), Qe(t), null);
      case 19:
        if ((we(Ee), (o = t.memoizedState), o === null)) return (Qe(t), null);
        if (((r = (t.flags & 128) !== 0), (a = o.rendering), a === null))
          if (r) Tr(o, !1);
          else {
            if (Me !== 0 || (e !== null && (e.flags & 128) !== 0))
              for (e = t.child; e !== null; ) {
                if (((a = Nl(e)), a !== null)) {
                  for (
                    t.flags |= 128,
                      Tr(o, !1),
                      r = a.updateQueue,
                      r !== null && ((t.updateQueue = r), (t.flags |= 4)),
                      t.subtreeFlags = 0,
                      r = n,
                      n = t.child;
                    n !== null;
                  )
                    ((o = n),
                      (e = r),
                      (o.flags &= 14680066),
                      (a = o.alternate),
                      a === null
                        ? ((o.childLanes = 0),
                          (o.lanes = e),
                          (o.child = null),
                          (o.subtreeFlags = 0),
                          (o.memoizedProps = null),
                          (o.memoizedState = null),
                          (o.updateQueue = null),
                          (o.dependencies = null),
                          (o.stateNode = null))
                        : ((o.childLanes = a.childLanes),
                          (o.lanes = a.lanes),
                          (o.child = a.child),
                          (o.subtreeFlags = 0),
                          (o.deletions = null),
                          (o.memoizedProps = a.memoizedProps),
                          (o.memoizedState = a.memoizedState),
                          (o.updateQueue = a.updateQueue),
                          (o.type = a.type),
                          (e = a.dependencies),
                          (o.dependencies = e === null ? null : { lanes: e.lanes, firstContext: e.firstContext })),
                      (n = n.sibling));
                  return (ye(Ee, (Ee.current & 1) | 2), t.child);
                }
                e = e.sibling;
              }
            o.tail !== null && Pe() > Yn && ((t.flags |= 128), (r = !0), Tr(o, !1), (t.lanes = 4194304));
          }
        else {
          if (!r)
            if (((e = Nl(a)), e !== null)) {
              if (
                ((t.flags |= 128),
                (r = !0),
                (n = e.updateQueue),
                n !== null && ((t.updateQueue = n), (t.flags |= 4)),
                Tr(o, !0),
                o.tail === null && o.tailMode === "hidden" && !a.alternate && !ke)
              )
                return (Qe(t), null);
            } else
              2 * Pe() - o.renderingStartTime > Yn &&
                n !== 1073741824 &&
                ((t.flags |= 128), (r = !0), Tr(o, !1), (t.lanes = 4194304));
          o.isBackwards
            ? ((a.sibling = t.child), (t.child = a))
            : ((n = o.last), n !== null ? (n.sibling = a) : (t.child = a), (o.last = a));
        }
        return o.tail !== null
          ? ((t = o.tail),
            (o.rendering = t),
            (o.tail = t.sibling),
            (o.renderingStartTime = Pe()),
            (t.sibling = null),
            (n = Ee.current),
            ye(Ee, r ? (n & 1) | 2 : n & 1),
            t)
          : (Qe(t), null);
      case 22:
      case 23:
        return (
          qo(),
          (r = t.memoizedState !== null),
          e !== null && (e.memoizedState !== null) !== r && (t.flags |= 8192),
          r && (t.mode & 1) !== 0 ? (ot & 1073741824) !== 0 && (Qe(t), t.subtreeFlags & 6 && (t.flags |= 8192)) : Qe(t),
          null
        );
      case 24:
        return null;
      case 25:
        return null;
    }
    throw Error(s(156, t.tag));
  }
  function Vd(e, t) {
    switch ((to(t), t.tag)) {
      case 1:
        return (Je(t.type) && ml(), (e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null);
      case 3:
        return (
          Vn(),
          we(Xe),
          we(We),
          mo(),
          (e = t.flags),
          (e & 65536) !== 0 && (e & 128) === 0 ? ((t.flags = (e & -65537) | 128), t) : null
        );
      case 5:
        return (po(t), null);
      case 13:
        if ((we(Ee), (e = t.memoizedState), e !== null && e.dehydrated !== null)) {
          if (t.alternate === null) throw Error(s(340));
          $n();
        }
        return ((e = t.flags), e & 65536 ? ((t.flags = (e & -65537) | 128), t) : null);
      case 19:
        return (we(Ee), null);
      case 4:
        return (Vn(), null);
      case 10:
        return (so(t.type._context), null);
      case 22:
      case 23:
        return (qo(), null);
      case 24:
        return null;
      default:
        return null;
    }
  }
  var Il = !1,
    Ke = !1,
    Qd = typeof WeakSet == "function" ? WeakSet : Set,
    V = null;
  function Kn(e, t) {
    var n = e.ref;
    if (n !== null)
      if (typeof n == "function")
        try {
          n(null);
        } catch (r) {
          je(e, t, r);
        }
      else n.current = null;
  }
  function Io(e, t, n) {
    try {
      n();
    } catch (r) {
      je(e, t, r);
    }
  }
  var Ka = !1;
  function Kd(e, t) {
    if (((Ki = tl), (e = Eu()), Ai(e))) {
      if ("selectionStart" in e) var n = { start: e.selectionStart, end: e.selectionEnd };
      else
        e: {
          n = ((n = e.ownerDocument) && n.defaultView) || window;
          var r = n.getSelection && n.getSelection();
          if (r && r.rangeCount !== 0) {
            n = r.anchorNode;
            var l = r.anchorOffset,
              o = r.focusNode;
            r = r.focusOffset;
            try {
              (n.nodeType, o.nodeType);
            } catch {
              n = null;
              break e;
            }
            var a = 0,
              v = -1,
              g = -1,
              N = 0,
              T = 0,
              O = e,
              P = null;
            t: for (;;) {
              for (
                var B;
                O !== n || (l !== 0 && O.nodeType !== 3) || (v = a + l),
                  O !== o || (r !== 0 && O.nodeType !== 3) || (g = a + r),
                  O.nodeType === 3 && (a += O.nodeValue.length),
                  (B = O.firstChild) !== null;
              )
                ((P = O), (O = B));
              for (;;) {
                if (O === e) break t;
                if ((P === n && ++N === l && (v = a), P === o && ++T === r && (g = a), (B = O.nextSibling) !== null))
                  break;
                ((O = P), (P = O.parentNode));
              }
              O = B;
            }
            n = v === -1 || g === -1 ? null : { start: v, end: g };
          } else n = null;
        }
      n = n || { start: 0, end: 0 };
    } else n = null;
    for (qi = { focusedElem: e, selectionRange: n }, tl = !1, V = t; V !== null; )
      if (((t = V), (e = t.child), (t.subtreeFlags & 1028) !== 0 && e !== null)) ((e.return = t), (V = e));
      else
        for (; V !== null; ) {
          t = V;
          try {
            var Q = t.alternate;
            if ((t.flags & 1024) !== 0)
              switch (t.tag) {
                case 0:
                case 11:
                case 15:
                  break;
                case 1:
                  if (Q !== null) {
                    var K = Q.memoizedProps,
                      Le = Q.memoizedState,
                      k = t.stateNode,
                      _ = k.getSnapshotBeforeUpdate(t.elementType === t.type ? K : _t(t.type, K), Le);
                    k.__reactInternalSnapshotBeforeUpdate = _;
                  }
                  break;
                case 3:
                  var E = t.stateNode.containerInfo;
                  E.nodeType === 1
                    ? (E.textContent = "")
                    : E.nodeType === 9 && E.documentElement && E.removeChild(E.documentElement);
                  break;
                case 5:
                case 6:
                case 4:
                case 17:
                  break;
                default:
                  throw Error(s(163));
              }
          } catch (M) {
            je(t, t.return, M);
          }
          if (((e = t.sibling), e !== null)) {
            ((e.return = t.return), (V = e));
            break;
          }
          V = t.return;
        }
    return ((Q = Ka), (Ka = !1), Q);
  }
  function Or(e, t, n) {
    var r = t.updateQueue;
    if (((r = r !== null ? r.lastEffect : null), r !== null)) {
      var l = (r = r.next);
      do {
        if ((l.tag & e) === e) {
          var o = l.destroy;
          ((l.destroy = void 0), o !== void 0 && Io(t, n, o));
        }
        l = l.next;
      } while (l !== r);
    }
  }
  function zl(e, t) {
    if (((t = t.updateQueue), (t = t !== null ? t.lastEffect : null), t !== null)) {
      var n = (t = t.next);
      do {
        if ((n.tag & e) === e) {
          var r = n.create;
          n.destroy = r();
        }
        n = n.next;
      } while (n !== t);
    }
  }
  function zo(e) {
    var t = e.ref;
    if (t !== null) {
      var n = e.stateNode;
      switch (e.tag) {
        case 5:
          e = n;
          break;
        default:
          e = n;
      }
      typeof t == "function" ? t(e) : (t.current = e);
    }
  }
  function qa(e) {
    var t = e.alternate;
    (t !== null && ((e.alternate = null), qa(t)),
      (e.child = null),
      (e.deletions = null),
      (e.sibling = null),
      e.tag === 5 &&
        ((t = e.stateNode), t !== null && (delete t[Ct], delete t[xr], delete t[Ji], delete t[jd], delete t[Pd])),
      (e.stateNode = null),
      (e.return = null),
      (e.dependencies = null),
      (e.memoizedProps = null),
      (e.memoizedState = null),
      (e.pendingProps = null),
      (e.stateNode = null),
      (e.updateQueue = null));
  }
  function Ya(e) {
    return e.tag === 5 || e.tag === 3 || e.tag === 4;
  }
  function Ga(e) {
    e: for (;;) {
      for (; e.sibling === null; ) {
        if (e.return === null || Ya(e.return)) return null;
        e = e.return;
      }
      for (e.sibling.return = e.return, e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18; ) {
        if (e.flags & 2 || e.child === null || e.tag === 4) continue e;
        ((e.child.return = e), (e = e.child));
      }
      if (!(e.flags & 2)) return e.stateNode;
    }
  }
  function Fo(e, t, n) {
    var r = e.tag;
    if (r === 5 || r === 6)
      ((e = e.stateNode),
        t
          ? n.nodeType === 8
            ? n.parentNode.insertBefore(e, t)
            : n.insertBefore(e, t)
          : (n.nodeType === 8 ? ((t = n.parentNode), t.insertBefore(e, n)) : ((t = n), t.appendChild(e)),
            (n = n._reactRootContainer),
            n != null || t.onclick !== null || (t.onclick = pl)));
    else if (r !== 4 && ((e = e.child), e !== null))
      for (Fo(e, t, n), e = e.sibling; e !== null; ) (Fo(e, t, n), (e = e.sibling));
  }
  function Ao(e, t, n) {
    var r = e.tag;
    if (r === 5 || r === 6) ((e = e.stateNode), t ? n.insertBefore(e, t) : n.appendChild(e));
    else if (r !== 4 && ((e = e.child), e !== null))
      for (Ao(e, t, n), e = e.sibling; e !== null; ) (Ao(e, t, n), (e = e.sibling));
  }
  var Be = null,
    wt = !1;
  function tn(e, t, n) {
    for (n = n.child; n !== null; ) (Xa(e, t, n), (n = n.sibling));
  }
  function Xa(e, t, n) {
    if (Et && typeof Et.onCommitFiberUnmount == "function")
      try {
        Et.onCommitFiberUnmount(Gr, n);
      } catch {}
    switch (n.tag) {
      case 5:
        Ke || Kn(n, t);
      case 6:
        var r = Be,
          l = wt;
        ((Be = null),
          tn(e, t, n),
          (Be = r),
          (wt = l),
          Be !== null &&
            (wt
              ? ((e = Be), (n = n.stateNode), e.nodeType === 8 ? e.parentNode.removeChild(n) : e.removeChild(n))
              : Be.removeChild(n.stateNode)));
        break;
      case 18:
        Be !== null &&
          (wt
            ? ((e = Be),
              (n = n.stateNode),
              e.nodeType === 8 ? Xi(e.parentNode, n) : e.nodeType === 1 && Xi(e, n),
              cr(e))
            : Xi(Be, n.stateNode));
        break;
      case 4:
        ((r = Be), (l = wt), (Be = n.stateNode.containerInfo), (wt = !0), tn(e, t, n), (Be = r), (wt = l));
        break;
      case 0:
      case 11:
      case 14:
      case 15:
        if (!Ke && ((r = n.updateQueue), r !== null && ((r = r.lastEffect), r !== null))) {
          l = r = r.next;
          do {
            var o = l,
              a = o.destroy;
            ((o = o.tag), a !== void 0 && ((o & 2) !== 0 || (o & 4) !== 0) && Io(n, t, a), (l = l.next));
          } while (l !== r);
        }
        tn(e, t, n);
        break;
      case 1:
        if (!Ke && (Kn(n, t), (r = n.stateNode), typeof r.componentWillUnmount == "function"))
          try {
            ((r.props = n.memoizedProps), (r.state = n.memoizedState), r.componentWillUnmount());
          } catch (v) {
            je(n, t, v);
          }
        tn(e, t, n);
        break;
      case 21:
        tn(e, t, n);
        break;
      case 22:
        n.mode & 1 ? ((Ke = (r = Ke) || n.memoizedState !== null), tn(e, t, n), (Ke = r)) : tn(e, t, n);
        break;
      default:
        tn(e, t, n);
    }
  }
  function Ja(e) {
    var t = e.updateQueue;
    if (t !== null) {
      e.updateQueue = null;
      var n = e.stateNode;
      (n === null && (n = e.stateNode = new Qd()),
        t.forEach(function (r) {
          var l = tp.bind(null, e, r);
          n.has(r) || (n.add(r), r.then(l, l));
        }));
    }
  }
  function xt(e, t) {
    var n = t.deletions;
    if (n !== null)
      for (var r = 0; r < n.length; r++) {
        var l = n[r];
        try {
          var o = e,
            a = t,
            v = a;
          e: for (; v !== null; ) {
            switch (v.tag) {
              case 5:
                ((Be = v.stateNode), (wt = !1));
                break e;
              case 3:
                ((Be = v.stateNode.containerInfo), (wt = !0));
                break e;
              case 4:
                ((Be = v.stateNode.containerInfo), (wt = !0));
                break e;
            }
            v = v.return;
          }
          if (Be === null) throw Error(s(160));
          (Xa(o, a, l), (Be = null), (wt = !1));
          var g = l.alternate;
          (g !== null && (g.return = null), (l.return = null));
        } catch (N) {
          je(l, t, N);
        }
      }
    if (t.subtreeFlags & 12854) for (t = t.child; t !== null; ) (Za(t, e), (t = t.sibling));
  }
  function Za(e, t) {
    var n = e.alternate,
      r = e.flags;
    switch (e.tag) {
      case 0:
      case 11:
      case 14:
      case 15:
        if ((xt(t, e), jt(e), r & 4)) {
          try {
            (Or(3, e, e.return), zl(3, e));
          } catch (K) {
            je(e, e.return, K);
          }
          try {
            Or(5, e, e.return);
          } catch (K) {
            je(e, e.return, K);
          }
        }
        break;
      case 1:
        (xt(t, e), jt(e), r & 512 && n !== null && Kn(n, n.return));
        break;
      case 5:
        if ((xt(t, e), jt(e), r & 512 && n !== null && Kn(n, n.return), e.flags & 32)) {
          var l = e.stateNode;
          try {
            bn(l, "");
          } catch (K) {
            je(e, e.return, K);
          }
        }
        if (r & 4 && ((l = e.stateNode), l != null)) {
          var o = e.memoizedProps,
            a = n !== null ? n.memoizedProps : o,
            v = e.type,
            g = e.updateQueue;
          if (((e.updateQueue = null), g !== null))
            try {
              (v === "input" && o.type === "radio" && o.name != null && Ns(l, o), hi(v, a));
              var N = hi(v, o);
              for (a = 0; a < g.length; a += 2) {
                var T = g[a],
                  O = g[a + 1];
                T === "style"
                  ? Ds(l, O)
                  : T === "dangerouslySetInnerHTML"
                    ? Os(l, O)
                    : T === "children"
                      ? bn(l, O)
                      : A(l, T, O, N);
              }
              switch (v) {
                case "input":
                  ai(l, o);
                  break;
                case "textarea":
                  Ps(l, o);
                  break;
                case "select":
                  var P = l._wrapperState.wasMultiple;
                  l._wrapperState.wasMultiple = !!o.multiple;
                  var B = o.value;
                  B != null
                    ? Cn(l, !!o.multiple, B, !1)
                    : P !== !!o.multiple &&
                      (o.defaultValue != null
                        ? Cn(l, !!o.multiple, o.defaultValue, !0)
                        : Cn(l, !!o.multiple, o.multiple ? [] : "", !1));
              }
              l[xr] = o;
            } catch (K) {
              je(e, e.return, K);
            }
        }
        break;
      case 6:
        if ((xt(t, e), jt(e), r & 4)) {
          if (e.stateNode === null) throw Error(s(162));
          ((l = e.stateNode), (o = e.memoizedProps));
          try {
            l.nodeValue = o;
          } catch (K) {
            je(e, e.return, K);
          }
        }
        break;
      case 3:
        if ((xt(t, e), jt(e), r & 4 && n !== null && n.memoizedState.isDehydrated))
          try {
            cr(t.containerInfo);
          } catch (K) {
            je(e, e.return, K);
          }
        break;
      case 4:
        (xt(t, e), jt(e));
        break;
      case 13:
        (xt(t, e),
          jt(e),
          (l = e.child),
          l.flags & 8192 &&
            ((o = l.memoizedState !== null),
            (l.stateNode.isHidden = o),
            !o || (l.alternate !== null && l.alternate.memoizedState !== null) || (Bo = Pe())),
          r & 4 && Ja(e));
        break;
      case 22:
        if (
          ((T = n !== null && n.memoizedState !== null),
          e.mode & 1 ? ((Ke = (N = Ke) || T), xt(t, e), (Ke = N)) : xt(t, e),
          jt(e),
          r & 8192)
        ) {
          if (((N = e.memoizedState !== null), (e.stateNode.isHidden = N) && !T && (e.mode & 1) !== 0))
            for (V = e, T = e.child; T !== null; ) {
              for (O = V = T; V !== null; ) {
                switch (((P = V), (B = P.child), P.tag)) {
                  case 0:
                  case 11:
                  case 14:
                  case 15:
                    Or(4, P, P.return);
                    break;
                  case 1:
                    Kn(P, P.return);
                    var Q = P.stateNode;
                    if (typeof Q.componentWillUnmount == "function") {
                      ((r = P), (n = P.return));
                      try {
                        ((t = r), (Q.props = t.memoizedProps), (Q.state = t.memoizedState), Q.componentWillUnmount());
                      } catch (K) {
                        je(r, n, K);
                      }
                    }
                    break;
                  case 5:
                    Kn(P, P.return);
                    break;
                  case 22:
                    if (P.memoizedState !== null) {
                      tc(O);
                      continue;
                    }
                }
                B !== null ? ((B.return = P), (V = B)) : tc(O);
              }
              T = T.sibling;
            }
          e: for (T = null, O = e; ; ) {
            if (O.tag === 5) {
              if (T === null) {
                T = O;
                try {
                  ((l = O.stateNode),
                    N
                      ? ((o = l.style),
                        typeof o.setProperty == "function"
                          ? o.setProperty("display", "none", "important")
                          : (o.display = "none"))
                      : ((v = O.stateNode),
                        (g = O.memoizedProps.style),
                        (a = g != null && g.hasOwnProperty("display") ? g.display : null),
                        (v.style.display = Ms("display", a))));
                } catch (K) {
                  je(e, e.return, K);
                }
              }
            } else if (O.tag === 6) {
              if (T === null)
                try {
                  O.stateNode.nodeValue = N ? "" : O.memoizedProps;
                } catch (K) {
                  je(e, e.return, K);
                }
            } else if (((O.tag !== 22 && O.tag !== 23) || O.memoizedState === null || O === e) && O.child !== null) {
              ((O.child.return = O), (O = O.child));
              continue;
            }
            if (O === e) break e;
            for (; O.sibling === null; ) {
              if (O.return === null || O.return === e) break e;
              (T === O && (T = null), (O = O.return));
            }
            (T === O && (T = null), (O.sibling.return = O.return), (O = O.sibling));
          }
        }
        break;
      case 19:
        (xt(t, e), jt(e), r & 4 && Ja(e));
        break;
      case 21:
        break;
      default:
        (xt(t, e), jt(e));
    }
  }
  function jt(e) {
    var t = e.flags;
    if (t & 2) {
      try {
        e: {
          for (var n = e.return; n !== null; ) {
            if (Ya(n)) {
              var r = n;
              break e;
            }
            n = n.return;
          }
          throw Error(s(160));
        }
        switch (r.tag) {
          case 5:
            var l = r.stateNode;
            r.flags & 32 && (bn(l, ""), (r.flags &= -33));
            var o = Ga(e);
            Ao(e, o, l);
            break;
          case 3:
          case 4:
            var a = r.stateNode.containerInfo,
              v = Ga(e);
            Fo(e, v, a);
            break;
          default:
            throw Error(s(161));
        }
      } catch (g) {
        je(e, e.return, g);
      }
      e.flags &= -3;
    }
    t & 4096 && (e.flags &= -4097);
  }
  function qd(e, t, n) {
    ((V = e), ba(e));
  }
  function ba(e, t, n) {
    for (var r = (e.mode & 1) !== 0; V !== null; ) {
      var l = V,
        o = l.child;
      if (l.tag === 22 && r) {
        var a = l.memoizedState !== null || Il;
        if (!a) {
          var v = l.alternate,
            g = (v !== null && v.memoizedState !== null) || Ke;
          v = Il;
          var N = Ke;
          if (((Il = a), (Ke = g) && !N))
            for (V = l; V !== null; )
              ((a = V),
                (g = a.child),
                a.tag === 22 && a.memoizedState !== null ? nc(l) : g !== null ? ((g.return = a), (V = g)) : nc(l));
          for (; o !== null; ) ((V = o), ba(o), (o = o.sibling));
          ((V = l), (Il = v), (Ke = N));
        }
        ec(e);
      } else (l.subtreeFlags & 8772) !== 0 && o !== null ? ((o.return = l), (V = o)) : ec(e);
    }
  }
  function ec(e) {
    for (; V !== null; ) {
      var t = V;
      if ((t.flags & 8772) !== 0) {
        var n = t.alternate;
        try {
          if ((t.flags & 8772) !== 0)
            switch (t.tag) {
              case 0:
              case 11:
              case 15:
                Ke || zl(5, t);
                break;
              case 1:
                var r = t.stateNode;
                if (t.flags & 4 && !Ke)
                  if (n === null) r.componentDidMount();
                  else {
                    var l = t.elementType === t.type ? n.memoizedProps : _t(t.type, n.memoizedProps);
                    r.componentDidUpdate(l, n.memoizedState, r.__reactInternalSnapshotBeforeUpdate);
                  }
                var o = t.updateQueue;
                o !== null && ta(t, o, r);
                break;
              case 3:
                var a = t.updateQueue;
                if (a !== null) {
                  if (((n = null), t.child !== null))
                    switch (t.child.tag) {
                      case 5:
                        n = t.child.stateNode;
                        break;
                      case 1:
                        n = t.child.stateNode;
                    }
                  ta(t, a, n);
                }
                break;
              case 5:
                var v = t.stateNode;
                if (n === null && t.flags & 4) {
                  n = v;
                  var g = t.memoizedProps;
                  switch (t.type) {
                    case "button":
                    case "input":
                    case "select":
                    case "textarea":
                      g.autoFocus && n.focus();
                      break;
                    case "img":
                      g.src && (n.src = g.src);
                  }
                }
                break;
              case 6:
                break;
              case 4:
                break;
              case 12:
                break;
              case 13:
                if (t.memoizedState === null) {
                  var N = t.alternate;
                  if (N !== null) {
                    var T = N.memoizedState;
                    if (T !== null) {
                      var O = T.dehydrated;
                      O !== null && cr(O);
                    }
                  }
                }
                break;
              case 19:
              case 17:
              case 21:
              case 22:
              case 23:
              case 25:
                break;
              default:
                throw Error(s(163));
            }
          Ke || (t.flags & 512 && zo(t));
        } catch (P) {
          je(t, t.return, P);
        }
      }
      if (t === e) {
        V = null;
        break;
      }
      if (((n = t.sibling), n !== null)) {
        ((n.return = t.return), (V = n));
        break;
      }
      V = t.return;
    }
  }
  function tc(e) {
    for (; V !== null; ) {
      var t = V;
      if (t === e) {
        V = null;
        break;
      }
      var n = t.sibling;
      if (n !== null) {
        ((n.return = t.return), (V = n));
        break;
      }
      V = t.return;
    }
  }
  function nc(e) {
    for (; V !== null; ) {
      var t = V;
      try {
        switch (t.tag) {
          case 0:
          case 11:
          case 15:
            var n = t.return;
            try {
              zl(4, t);
            } catch (g) {
              je(t, n, g);
            }
            break;
          case 1:
            var r = t.stateNode;
            if (typeof r.componentDidMount == "function") {
              var l = t.return;
              try {
                r.componentDidMount();
              } catch (g) {
                je(t, l, g);
              }
            }
            var o = t.return;
            try {
              zo(t);
            } catch (g) {
              je(t, o, g);
            }
            break;
          case 5:
            var a = t.return;
            try {
              zo(t);
            } catch (g) {
              je(t, a, g);
            }
        }
      } catch (g) {
        je(t, t.return, g);
      }
      if (t === e) {
        V = null;
        break;
      }
      var v = t.sibling;
      if (v !== null) {
        ((v.return = t.return), (V = v));
        break;
      }
      V = t.return;
    }
  }
  var Yd = Math.ceil,
    Fl = le.ReactCurrentDispatcher,
    Uo = le.ReactCurrentOwner,
    dt = le.ReactCurrentBatchConfig,
    se = 0,
    Ue = null,
    Te = null,
    He = 0,
    ot = 0,
    qn = Xt(0),
    Me = 0,
    Mr = null,
    wn = 0,
    Al = 0,
    $o = 0,
    Dr = null,
    be = null,
    Bo = 0,
    Yn = 1 / 0,
    At = null,
    Ul = !1,
    Ho = null,
    nn = null,
    $l = !1,
    rn = null,
    Bl = 0,
    Ir = 0,
    Wo = null,
    Hl = -1,
    Wl = 0;
  function Ye() {
    return (se & 6) !== 0 ? Pe() : Hl !== -1 ? Hl : (Hl = Pe());
  }
  function ln(e) {
    return (e.mode & 1) === 0
      ? 1
      : (se & 2) !== 0 && He !== 0
        ? He & -He
        : Td.transition !== null
          ? (Wl === 0 && (Wl = Gs()), Wl)
          : ((e = pe), e !== 0 || ((e = window.event), (e = e === void 0 ? 16 : lu(e.type))), e);
  }
  function St(e, t, n, r) {
    if (50 < Ir) throw ((Ir = 0), (Wo = null), Error(s(185)));
    (ir(e, n, r),
      ((se & 2) === 0 || e !== Ue) &&
        (e === Ue && ((se & 2) === 0 && (Al |= n), Me === 4 && on(e, He)),
        et(e, r),
        n === 1 && se === 0 && (t.mode & 1) === 0 && ((Yn = Pe() + 500), yl && Zt())));
  }
  function et(e, t) {
    var n = e.callbackNode;
    Tf(e, t);
    var r = Zr(e, e === Ue ? He : 0);
    if (r === 0) (n !== null && Ks(n), (e.callbackNode = null), (e.callbackPriority = 0));
    else if (((t = r & -r), e.callbackPriority !== t)) {
      if ((n != null && Ks(n), t === 1))
        (e.tag === 0 ? Ld(lc.bind(null, e)) : Wu(lc.bind(null, e)),
          Nd(function () {
            (se & 6) === 0 && Zt();
          }),
          (n = null));
      else {
        switch (Xs(r)) {
          case 1:
            n = xi;
            break;
          case 4:
            n = qs;
            break;
          case 16:
            n = Yr;
            break;
          case 536870912:
            n = Ys;
            break;
          default:
            n = Yr;
        }
        n = dc(n, rc.bind(null, e));
      }
      ((e.callbackPriority = t), (e.callbackNode = n));
    }
  }
  function rc(e, t) {
    if (((Hl = -1), (Wl = 0), (se & 6) !== 0)) throw Error(s(327));
    var n = e.callbackNode;
    if (Gn() && e.callbackNode !== n) return null;
    var r = Zr(e, e === Ue ? He : 0);
    if (r === 0) return null;
    if ((r & 30) !== 0 || (r & e.expiredLanes) !== 0 || t) t = Vl(e, r);
    else {
      t = r;
      var l = se;
      se |= 2;
      var o = oc();
      (Ue !== e || He !== t) && ((At = null), (Yn = Pe() + 500), Sn(e, t));
      do
        try {
          Jd();
          break;
        } catch (v) {
          ic(e, v);
        }
      while (!0);
      (oo(), (Fl.current = o), (se = l), Te !== null ? (t = 0) : ((Ue = null), (He = 0), (t = Me)));
    }
    if (t !== 0) {
      if ((t === 2 && ((l = Si(e)), l !== 0 && ((r = l), (t = Vo(e, l)))), t === 1))
        throw ((n = Mr), Sn(e, 0), on(e, r), et(e, Pe()), n);
      if (t === 6) on(e, r);
      else {
        if (
          ((l = e.current.alternate),
          (r & 30) === 0 &&
            !Gd(l) &&
            ((t = Vl(e, r)), t === 2 && ((o = Si(e)), o !== 0 && ((r = o), (t = Vo(e, o)))), t === 1))
        )
          throw ((n = Mr), Sn(e, 0), on(e, r), et(e, Pe()), n);
        switch (((e.finishedWork = l), (e.finishedLanes = r), t)) {
          case 0:
          case 1:
            throw Error(s(345));
          case 2:
            kn(e, be, At);
            break;
          case 3:
            if ((on(e, r), (r & 130023424) === r && ((t = Bo + 500 - Pe()), 10 < t))) {
              if (Zr(e, 0) !== 0) break;
              if (((l = e.suspendedLanes), (l & r) !== r)) {
                (Ye(), (e.pingedLanes |= e.suspendedLanes & l));
                break;
              }
              e.timeoutHandle = Gi(kn.bind(null, e, be, At), t);
              break;
            }
            kn(e, be, At);
            break;
          case 4:
            if ((on(e, r), (r & 4194240) === r)) break;
            for (t = e.eventTimes, l = -1; 0 < r; ) {
              var a = 31 - vt(r);
              ((o = 1 << a), (a = t[a]), a > l && (l = a), (r &= ~o));
            }
            if (
              ((r = l),
              (r = Pe() - r),
              (r =
                (120 > r
                  ? 120
                  : 480 > r
                    ? 480
                    : 1080 > r
                      ? 1080
                      : 1920 > r
                        ? 1920
                        : 3e3 > r
                          ? 3e3
                          : 4320 > r
                            ? 4320
                            : 1960 * Yd(r / 1960)) - r),
              10 < r)
            ) {
              e.timeoutHandle = Gi(kn.bind(null, e, be, At), r);
              break;
            }
            kn(e, be, At);
            break;
          case 5:
            kn(e, be, At);
            break;
          default:
            throw Error(s(329));
        }
      }
    }
    return (et(e, Pe()), e.callbackNode === n ? rc.bind(null, e) : null);
  }
  function Vo(e, t) {
    var n = Dr;
    return (
      e.current.memoizedState.isDehydrated && (Sn(e, t).flags |= 256),
      (e = Vl(e, t)),
      e !== 2 && ((t = be), (be = n), t !== null && Qo(t)),
      e
    );
  }
  function Qo(e) {
    be === null ? (be = e) : be.push.apply(be, e);
  }
  function Gd(e) {
    for (var t = e; ; ) {
      if (t.flags & 16384) {
        var n = t.updateQueue;
        if (n !== null && ((n = n.stores), n !== null))
          for (var r = 0; r < n.length; r++) {
            var l = n[r],
              o = l.getSnapshot;
            l = l.value;
            try {
              if (!yt(o(), l)) return !1;
            } catch {
              return !1;
            }
          }
      }
      if (((n = t.child), t.subtreeFlags & 16384 && n !== null)) ((n.return = t), (t = n));
      else {
        if (t === e) break;
        for (; t.sibling === null; ) {
          if (t.return === null || t.return === e) return !0;
          t = t.return;
        }
        ((t.sibling.return = t.return), (t = t.sibling));
      }
    }
    return !0;
  }
  function on(e, t) {
    for (t &= ~$o, t &= ~Al, e.suspendedLanes |= t, e.pingedLanes &= ~t, e = e.expirationTimes; 0 < t; ) {
      var n = 31 - vt(t),
        r = 1 << n;
      ((e[n] = -1), (t &= ~r));
    }
  }
  function lc(e) {
    if ((se & 6) !== 0) throw Error(s(327));
    Gn();
    var t = Zr(e, 0);
    if ((t & 1) === 0) return (et(e, Pe()), null);
    var n = Vl(e, t);
    if (e.tag !== 0 && n === 2) {
      var r = Si(e);
      r !== 0 && ((t = r), (n = Vo(e, r)));
    }
    if (n === 1) throw ((n = Mr), Sn(e, 0), on(e, t), et(e, Pe()), n);
    if (n === 6) throw Error(s(345));
    return ((e.finishedWork = e.current.alternate), (e.finishedLanes = t), kn(e, be, At), et(e, Pe()), null);
  }
  function Ko(e, t) {
    var n = se;
    se |= 1;
    try {
      return e(t);
    } finally {
      ((se = n), se === 0 && ((Yn = Pe() + 500), yl && Zt()));
    }
  }
  function xn(e) {
    rn !== null && rn.tag === 0 && (se & 6) === 0 && Gn();
    var t = se;
    se |= 1;
    var n = dt.transition,
      r = pe;
    try {
      if (((dt.transition = null), (pe = 1), e)) return e();
    } finally {
      ((pe = r), (dt.transition = n), (se = t), (se & 6) === 0 && Zt());
    }
  }
  function qo() {
    ((ot = qn.current), we(qn));
  }
  function Sn(e, t) {
    ((e.finishedWork = null), (e.finishedLanes = 0));
    var n = e.timeoutHandle;
    if ((n !== -1 && ((e.timeoutHandle = -1), Cd(n)), Te !== null))
      for (n = Te.return; n !== null; ) {
        var r = n;
        switch ((to(r), r.tag)) {
          case 1:
            ((r = r.type.childContextTypes), r != null && ml());
            break;
          case 3:
            (Vn(), we(Xe), we(We), mo());
            break;
          case 5:
            po(r);
            break;
          case 4:
            Vn();
            break;
          case 13:
            we(Ee);
            break;
          case 19:
            we(Ee);
            break;
          case 10:
            so(r.type._context);
            break;
          case 22:
          case 23:
            qo();
        }
        n = n.return;
      }
    if (
      ((Ue = e),
      (Te = e = sn(e.current, null)),
      (He = ot = t),
      (Me = 0),
      (Mr = null),
      ($o = Al = wn = 0),
      (be = Dr = null),
      yn !== null)
    ) {
      for (t = 0; t < yn.length; t++)
        if (((n = yn[t]), (r = n.interleaved), r !== null)) {
          n.interleaved = null;
          var l = r.next,
            o = n.pending;
          if (o !== null) {
            var a = o.next;
            ((o.next = l), (r.next = a));
          }
          n.pending = r;
        }
      yn = null;
    }
    return e;
  }
  function ic(e, t) {
    do {
      var n = Te;
      try {
        if ((oo(), (Rl.current = Tl), jl)) {
          for (var r = Ce.memoizedState; r !== null; ) {
            var l = r.queue;
            (l !== null && (l.pending = null), (r = r.next));
          }
          jl = !1;
        }
        if (
          ((_n = 0), (Ae = Oe = Ce = null), (Rr = !1), (jr = 0), (Uo.current = null), n === null || n.return === null)
        ) {
          ((Me = 1), (Mr = t), (Te = null));
          break;
        }
        e: {
          var o = e,
            a = n.return,
            v = n,
            g = t;
          if (((t = He), (v.flags |= 32768), g !== null && typeof g == "object" && typeof g.then == "function")) {
            var N = g,
              T = v,
              O = T.tag;
            if ((T.mode & 1) === 0 && (O === 0 || O === 11 || O === 15)) {
              var P = T.alternate;
              P
                ? ((T.updateQueue = P.updateQueue), (T.memoizedState = P.memoizedState), (T.lanes = P.lanes))
                : ((T.updateQueue = null), (T.memoizedState = null));
            }
            var B = La(a);
            if (B !== null) {
              ((B.flags &= -257), Ta(B, a, v, o, t), B.mode & 1 && Pa(o, N, t), (t = B), (g = N));
              var Q = t.updateQueue;
              if (Q === null) {
                var K = new Set();
                (K.add(g), (t.updateQueue = K));
              } else Q.add(g);
              break e;
            } else {
              if ((t & 1) === 0) {
                (Pa(o, N, t), Yo());
                break e;
              }
              g = Error(s(426));
            }
          } else if (ke && v.mode & 1) {
            var Le = La(a);
            if (Le !== null) {
              ((Le.flags & 65536) === 0 && (Le.flags |= 256), Ta(Le, a, v, o, t), lo(Qn(g, v)));
              break e;
            }
          }
          ((o = g = Qn(g, v)), Me !== 4 && (Me = 2), Dr === null ? (Dr = [o]) : Dr.push(o), (o = a));
          do {
            switch (o.tag) {
              case 3:
                ((o.flags |= 65536), (t &= -t), (o.lanes |= t));
                var k = Ra(o, g, t);
                ea(o, k);
                break e;
              case 1:
                v = g;
                var _ = o.type,
                  E = o.stateNode;
                if (
                  (o.flags & 128) === 0 &&
                  (typeof _.getDerivedStateFromError == "function" ||
                    (E !== null && typeof E.componentDidCatch == "function" && (nn === null || !nn.has(E))))
                ) {
                  ((o.flags |= 65536), (t &= -t), (o.lanes |= t));
                  var M = ja(o, v, t);
                  ea(o, M);
                  break e;
                }
            }
            o = o.return;
          } while (o !== null);
        }
        uc(n);
      } catch (q) {
        ((t = q), Te === n && n !== null && (Te = n = n.return));
        continue;
      }
      break;
    } while (!0);
  }
  function oc() {
    var e = Fl.current;
    return ((Fl.current = Tl), e === null ? Tl : e);
  }
  function Yo() {
    ((Me === 0 || Me === 3 || Me === 2) && (Me = 4),
      Ue === null || ((wn & 268435455) === 0 && (Al & 268435455) === 0) || on(Ue, He));
  }
  function Vl(e, t) {
    var n = se;
    se |= 2;
    var r = oc();
    (Ue !== e || He !== t) && ((At = null), Sn(e, t));
    do
      try {
        Xd();
        break;
      } catch (l) {
        ic(e, l);
      }
    while (!0);
    if ((oo(), (se = n), (Fl.current = r), Te !== null)) throw Error(s(261));
    return ((Ue = null), (He = 0), Me);
  }
  function Xd() {
    for (; Te !== null; ) sc(Te);
  }
  function Jd() {
    for (; Te !== null && !Sf(); ) sc(Te);
  }
  function sc(e) {
    var t = fc(e.alternate, e, ot);
    ((e.memoizedProps = e.pendingProps), t === null ? uc(e) : (Te = t), (Uo.current = null));
  }
  function uc(e) {
    var t = e;
    do {
      var n = t.alternate;
      if (((e = t.return), (t.flags & 32768) === 0)) {
        if (((n = Wd(n, t, ot)), n !== null)) {
          Te = n;
          return;
        }
      } else {
        if (((n = Vd(n, t)), n !== null)) {
          ((n.flags &= 32767), (Te = n));
          return;
        }
        if (e !== null) ((e.flags |= 32768), (e.subtreeFlags = 0), (e.deletions = null));
        else {
          ((Me = 6), (Te = null));
          return;
        }
      }
      if (((t = t.sibling), t !== null)) {
        Te = t;
        return;
      }
      Te = t = e;
    } while (t !== null);
    Me === 0 && (Me = 5);
  }
  function kn(e, t, n) {
    var r = pe,
      l = dt.transition;
    try {
      ((dt.transition = null), (pe = 1), Zd(e, t, n, r));
    } finally {
      ((dt.transition = l), (pe = r));
    }
    return null;
  }
  function Zd(e, t, n, r) {
    do Gn();
    while (rn !== null);
    if ((se & 6) !== 0) throw Error(s(327));
    n = e.finishedWork;
    var l = e.finishedLanes;
    if (n === null) return null;
    if (((e.finishedWork = null), (e.finishedLanes = 0), n === e.current)) throw Error(s(177));
    ((e.callbackNode = null), (e.callbackPriority = 0));
    var o = n.lanes | n.childLanes;
    if (
      (Of(e, o),
      e === Ue && ((Te = Ue = null), (He = 0)),
      ((n.subtreeFlags & 2064) === 0 && (n.flags & 2064) === 0) ||
        $l ||
        (($l = !0),
        dc(Yr, function () {
          return (Gn(), null);
        })),
      (o = (n.flags & 15990) !== 0),
      (n.subtreeFlags & 15990) !== 0 || o)
    ) {
      ((o = dt.transition), (dt.transition = null));
      var a = pe;
      pe = 1;
      var v = se;
      ((se |= 4),
        (Uo.current = null),
        Kd(e, n),
        Za(n, e),
        gd(qi),
        (tl = !!Ki),
        (qi = Ki = null),
        (e.current = n),
        qd(n),
        kf(),
        (se = v),
        (pe = a),
        (dt.transition = o));
    } else e.current = n;
    if (
      ($l && (($l = !1), (rn = e), (Bl = l)),
      (o = e.pendingLanes),
      o === 0 && (nn = null),
      Nf(n.stateNode),
      et(e, Pe()),
      t !== null)
    )
      for (r = e.onRecoverableError, n = 0; n < t.length; n++)
        ((l = t[n]), r(l.value, { componentStack: l.stack, digest: l.digest }));
    if (Ul) throw ((Ul = !1), (e = Ho), (Ho = null), e);
    return (
      (Bl & 1) !== 0 && e.tag !== 0 && Gn(),
      (o = e.pendingLanes),
      (o & 1) !== 0 ? (e === Wo ? Ir++ : ((Ir = 0), (Wo = e))) : (Ir = 0),
      Zt(),
      null
    );
  }
  function Gn() {
    if (rn !== null) {
      var e = Xs(Bl),
        t = dt.transition,
        n = pe;
      try {
        if (((dt.transition = null), (pe = 16 > e ? 16 : e), rn === null)) var r = !1;
        else {
          if (((e = rn), (rn = null), (Bl = 0), (se & 6) !== 0)) throw Error(s(331));
          var l = se;
          for (se |= 4, V = e.current; V !== null; ) {
            var o = V,
              a = o.child;
            if ((V.flags & 16) !== 0) {
              var v = o.deletions;
              if (v !== null) {
                for (var g = 0; g < v.length; g++) {
                  var N = v[g];
                  for (V = N; V !== null; ) {
                    var T = V;
                    switch (T.tag) {
                      case 0:
                      case 11:
                      case 15:
                        Or(8, T, o);
                    }
                    var O = T.child;
                    if (O !== null) ((O.return = T), (V = O));
                    else
                      for (; V !== null; ) {
                        T = V;
                        var P = T.sibling,
                          B = T.return;
                        if ((qa(T), T === N)) {
                          V = null;
                          break;
                        }
                        if (P !== null) {
                          ((P.return = B), (V = P));
                          break;
                        }
                        V = B;
                      }
                  }
                }
                var Q = o.alternate;
                if (Q !== null) {
                  var K = Q.child;
                  if (K !== null) {
                    Q.child = null;
                    do {
                      var Le = K.sibling;
                      ((K.sibling = null), (K = Le));
                    } while (K !== null);
                  }
                }
                V = o;
              }
            }
            if ((o.subtreeFlags & 2064) !== 0 && a !== null) ((a.return = o), (V = a));
            else
              e: for (; V !== null; ) {
                if (((o = V), (o.flags & 2048) !== 0))
                  switch (o.tag) {
                    case 0:
                    case 11:
                    case 15:
                      Or(9, o, o.return);
                  }
                var k = o.sibling;
                if (k !== null) {
                  ((k.return = o.return), (V = k));
                  break e;
                }
                V = o.return;
              }
          }
          var _ = e.current;
          for (V = _; V !== null; ) {
            a = V;
            var E = a.child;
            if ((a.subtreeFlags & 2064) !== 0 && E !== null) ((E.return = a), (V = E));
            else
              e: for (a = _; V !== null; ) {
                if (((v = V), (v.flags & 2048) !== 0))
                  try {
                    switch (v.tag) {
                      case 0:
                      case 11:
                      case 15:
                        zl(9, v);
                    }
                  } catch (q) {
                    je(v, v.return, q);
                  }
                if (v === a) {
                  V = null;
                  break e;
                }
                var M = v.sibling;
                if (M !== null) {
                  ((M.return = v.return), (V = M));
                  break e;
                }
                V = v.return;
              }
          }
          if (((se = l), Zt(), Et && typeof Et.onPostCommitFiberRoot == "function"))
            try {
              Et.onPostCommitFiberRoot(Gr, e);
            } catch {}
          r = !0;
        }
        return r;
      } finally {
        ((pe = n), (dt.transition = t));
      }
    }
    return !1;
  }
  function ac(e, t, n) {
    ((t = Qn(n, t)), (t = Ra(e, t, 1)), (e = en(e, t, 1)), (t = Ye()), e !== null && (ir(e, 1, t), et(e, t)));
  }
  function je(e, t, n) {
    if (e.tag === 3) ac(e, e, n);
    else
      for (; t !== null; ) {
        if (t.tag === 3) {
          ac(t, e, n);
          break;
        } else if (t.tag === 1) {
          var r = t.stateNode;
          if (
            typeof t.type.getDerivedStateFromError == "function" ||
            (typeof r.componentDidCatch == "function" && (nn === null || !nn.has(r)))
          ) {
            ((e = Qn(n, e)), (e = ja(t, e, 1)), (t = en(t, e, 1)), (e = Ye()), t !== null && (ir(t, 1, e), et(t, e)));
            break;
          }
        }
        t = t.return;
      }
  }
  function bd(e, t, n) {
    var r = e.pingCache;
    (r !== null && r.delete(t),
      (t = Ye()),
      (e.pingedLanes |= e.suspendedLanes & n),
      Ue === e &&
        (He & n) === n &&
        (Me === 4 || (Me === 3 && (He & 130023424) === He && 500 > Pe() - Bo) ? Sn(e, 0) : ($o |= n)),
      et(e, t));
  }
  function cc(e, t) {
    t === 0 && ((e.mode & 1) === 0 ? (t = 1) : ((t = Jr), (Jr <<= 1), (Jr & 130023424) === 0 && (Jr = 4194304)));
    var n = Ye();
    ((e = It(e, t)), e !== null && (ir(e, t, n), et(e, n)));
  }
  function ep(e) {
    var t = e.memoizedState,
      n = 0;
    (t !== null && (n = t.retryLane), cc(e, n));
  }
  function tp(e, t) {
    var n = 0;
    switch (e.tag) {
      case 13:
        var r = e.stateNode,
          l = e.memoizedState;
        l !== null && (n = l.retryLane);
        break;
      case 19:
        r = e.stateNode;
        break;
      default:
        throw Error(s(314));
    }
    (r !== null && r.delete(t), cc(e, n));
  }
  var fc;
  fc = function (e, t, n) {
    if (e !== null)
      if (e.memoizedProps !== t.pendingProps || Xe.current) Ze = !0;
      else {
        if ((e.lanes & n) === 0 && (t.flags & 128) === 0) return ((Ze = !1), Hd(e, t, n));
        Ze = (e.flags & 131072) !== 0;
      }
    else ((Ze = !1), ke && (t.flags & 1048576) !== 0 && Vu(t, _l, t.index));
    switch (((t.lanes = 0), t.tag)) {
      case 2:
        var r = t.type;
        (Dl(e, t), (e = t.pendingProps));
        var l = Fn(t, We.current);
        (Wn(t, n), (l = go(null, t, r, e, l, n)));
        var o = _o();
        return (
          (t.flags |= 1),
          typeof l == "object" && l !== null && typeof l.render == "function" && l.$$typeof === void 0
            ? ((t.tag = 1),
              (t.memoizedState = null),
              (t.updateQueue = null),
              Je(r) ? ((o = !0), vl(t)) : (o = !1),
              (t.memoizedState = l.state !== null && l.state !== void 0 ? l.state : null),
              co(t),
              (l.updater = Ol),
              (t.stateNode = l),
              (l._reactInternals = t),
              Co(t, r, e, n),
              (t = Po(null, t, r, !0, o, n)))
            : ((t.tag = 0), ke && o && eo(t), qe(null, t, l, n), (t = t.child)),
          t
        );
      case 16:
        r = t.elementType;
        e: {
          switch (
            (Dl(e, t),
            (e = t.pendingProps),
            (l = r._init),
            (r = l(r._payload)),
            (t.type = r),
            (l = t.tag = rp(r)),
            (e = _t(r, e)),
            l)
          ) {
            case 0:
              t = jo(null, t, r, e, n);
              break e;
            case 1:
              t = Fa(null, t, r, e, n);
              break e;
            case 11:
              t = Oa(null, t, r, e, n);
              break e;
            case 14:
              t = Ma(null, t, r, _t(r.type, e), n);
              break e;
          }
          throw Error(s(306, r, ""));
        }
        return t;
      case 0:
        return ((r = t.type), (l = t.pendingProps), (l = t.elementType === r ? l : _t(r, l)), jo(e, t, r, l, n));
      case 1:
        return ((r = t.type), (l = t.pendingProps), (l = t.elementType === r ? l : _t(r, l)), Fa(e, t, r, l, n));
      case 3:
        e: {
          if ((Aa(t), e === null)) throw Error(s(387));
          ((r = t.pendingProps), (o = t.memoizedState), (l = o.element), bu(e, t), Cl(t, r, null, n));
          var a = t.memoizedState;
          if (((r = a.element), o.isDehydrated))
            if (
              ((o = {
                element: r,
                isDehydrated: !1,
                cache: a.cache,
                pendingSuspenseBoundaries: a.pendingSuspenseBoundaries,
                transitions: a.transitions,
              }),
              (t.updateQueue.baseState = o),
              (t.memoizedState = o),
              t.flags & 256)
            ) {
              ((l = Qn(Error(s(423)), t)), (t = Ua(e, t, r, n, l)));
              break e;
            } else if (r !== l) {
              ((l = Qn(Error(s(424)), t)), (t = Ua(e, t, r, n, l)));
              break e;
            } else
              for (
                it = Gt(t.stateNode.containerInfo.firstChild),
                  lt = t,
                  ke = !0,
                  gt = null,
                  n = Ju(t, null, r, n),
                  t.child = n;
                n;
              )
                ((n.flags = (n.flags & -3) | 4096), (n = n.sibling));
          else {
            if (($n(), r === l)) {
              t = Ft(e, t, n);
              break e;
            }
            qe(e, t, r, n);
          }
          t = t.child;
        }
        return t;
      case 5:
        return (
          na(t),
          e === null && ro(t),
          (r = t.type),
          (l = t.pendingProps),
          (o = e !== null ? e.memoizedProps : null),
          (a = l.children),
          Yi(r, l) ? (a = null) : o !== null && Yi(r, o) && (t.flags |= 32),
          za(e, t),
          qe(e, t, a, n),
          t.child
        );
      case 6:
        return (e === null && ro(t), null);
      case 13:
        return $a(e, t, n);
      case 4:
        return (
          fo(t, t.stateNode.containerInfo),
          (r = t.pendingProps),
          e === null ? (t.child = Bn(t, null, r, n)) : qe(e, t, r, n),
          t.child
        );
      case 11:
        return ((r = t.type), (l = t.pendingProps), (l = t.elementType === r ? l : _t(r, l)), Oa(e, t, r, l, n));
      case 7:
        return (qe(e, t, t.pendingProps, n), t.child);
      case 8:
        return (qe(e, t, t.pendingProps.children, n), t.child);
      case 12:
        return (qe(e, t, t.pendingProps.children, n), t.child);
      case 10:
        e: {
          if (
            ((r = t.type._context),
            (l = t.pendingProps),
            (o = t.memoizedProps),
            (a = l.value),
            ye(Sl, r._currentValue),
            (r._currentValue = a),
            o !== null)
          )
            if (yt(o.value, a)) {
              if (o.children === l.children && !Xe.current) {
                t = Ft(e, t, n);
                break e;
              }
            } else
              for (o = t.child, o !== null && (o.return = t); o !== null; ) {
                var v = o.dependencies;
                if (v !== null) {
                  a = o.child;
                  for (var g = v.firstContext; g !== null; ) {
                    if (g.context === r) {
                      if (o.tag === 1) {
                        ((g = zt(-1, n & -n)), (g.tag = 2));
                        var N = o.updateQueue;
                        if (N !== null) {
                          N = N.shared;
                          var T = N.pending;
                          (T === null ? (g.next = g) : ((g.next = T.next), (T.next = g)), (N.pending = g));
                        }
                      }
                      ((o.lanes |= n),
                        (g = o.alternate),
                        g !== null && (g.lanes |= n),
                        uo(o.return, n, t),
                        (v.lanes |= n));
                      break;
                    }
                    g = g.next;
                  }
                } else if (o.tag === 10) a = o.type === t.type ? null : o.child;
                else if (o.tag === 18) {
                  if (((a = o.return), a === null)) throw Error(s(341));
                  ((a.lanes |= n), (v = a.alternate), v !== null && (v.lanes |= n), uo(a, n, t), (a = o.sibling));
                } else a = o.child;
                if (a !== null) a.return = o;
                else
                  for (a = o; a !== null; ) {
                    if (a === t) {
                      a = null;
                      break;
                    }
                    if (((o = a.sibling), o !== null)) {
                      ((o.return = a.return), (a = o));
                      break;
                    }
                    a = a.return;
                  }
                o = a;
              }
          (qe(e, t, l.children, n), (t = t.child));
        }
        return t;
      case 9:
        return (
          (l = t.type),
          (r = t.pendingProps.children),
          Wn(t, n),
          (l = ct(l)),
          (r = r(l)),
          (t.flags |= 1),
          qe(e, t, r, n),
          t.child
        );
      case 14:
        return ((r = t.type), (l = _t(r, t.pendingProps)), (l = _t(r.type, l)), Ma(e, t, r, l, n));
      case 15:
        return Da(e, t, t.type, t.pendingProps, n);
      case 17:
        return (
          (r = t.type),
          (l = t.pendingProps),
          (l = t.elementType === r ? l : _t(r, l)),
          Dl(e, t),
          (t.tag = 1),
          Je(r) ? ((e = !0), vl(t)) : (e = !1),
          Wn(t, n),
          Ca(t, r, l),
          Co(t, r, l, n),
          Po(null, t, r, !0, e, n)
        );
      case 19:
        return Ha(e, t, n);
      case 22:
        return Ia(e, t, n);
    }
    throw Error(s(156, t.tag));
  };
  function dc(e, t) {
    return Qs(e, t);
  }
  function np(e, t, n, r) {
    ((this.tag = e),
      (this.key = n),
      (this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null),
      (this.index = 0),
      (this.ref = null),
      (this.pendingProps = t),
      (this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null),
      (this.mode = r),
      (this.subtreeFlags = this.flags = 0),
      (this.deletions = null),
      (this.childLanes = this.lanes = 0),
      (this.alternate = null));
  }
  function pt(e, t, n, r) {
    return new np(e, t, n, r);
  }
  function Go(e) {
    return ((e = e.prototype), !(!e || !e.isReactComponent));
  }
  function rp(e) {
    if (typeof e == "function") return Go(e) ? 1 : 0;
    if (e != null) {
      if (((e = e.$$typeof), e === st)) return 11;
      if (e === ee) return 14;
    }
    return 2;
  }
  function sn(e, t) {
    var n = e.alternate;
    return (
      n === null
        ? ((n = pt(e.tag, t, e.key, e.mode)),
          (n.elementType = e.elementType),
          (n.type = e.type),
          (n.stateNode = e.stateNode),
          (n.alternate = e),
          (e.alternate = n))
        : ((n.pendingProps = t), (n.type = e.type), (n.flags = 0), (n.subtreeFlags = 0), (n.deletions = null)),
      (n.flags = e.flags & 14680064),
      (n.childLanes = e.childLanes),
      (n.lanes = e.lanes),
      (n.child = e.child),
      (n.memoizedProps = e.memoizedProps),
      (n.memoizedState = e.memoizedState),
      (n.updateQueue = e.updateQueue),
      (t = e.dependencies),
      (n.dependencies = t === null ? null : { lanes: t.lanes, firstContext: t.firstContext }),
      (n.sibling = e.sibling),
      (n.index = e.index),
      (n.ref = e.ref),
      n
    );
  }
  function Ql(e, t, n, r, l, o) {
    var a = 2;
    if (((r = e), typeof e == "function")) Go(e) && (a = 1);
    else if (typeof e == "string") a = 5;
    else
      e: switch (e) {
        case xe:
          return En(n.children, l, o, t);
        case Re:
          ((a = 8), (l |= 8));
          break;
        case Ie:
          return ((e = pt(12, n, t, l | 2)), (e.elementType = Ie), (e.lanes = o), e);
        case Fe:
          return ((e = pt(13, n, t, l)), (e.elementType = Fe), (e.lanes = o), e);
        case G:
          return ((e = pt(19, n, t, l)), (e.elementType = G), (e.lanes = o), e);
        case oe:
          return Kl(n, l, o, t);
        default:
          if (typeof e == "object" && e !== null)
            switch (e.$$typeof) {
              case ze:
                a = 10;
                break e;
              case kt:
                a = 9;
                break e;
              case st:
                a = 11;
                break e;
              case ee:
                a = 14;
                break e;
              case me:
                ((a = 16), (r = null));
                break e;
            }
          throw Error(s(130, e == null ? e : typeof e, ""));
      }
    return ((t = pt(a, n, t, l)), (t.elementType = e), (t.type = r), (t.lanes = o), t);
  }
  function En(e, t, n, r) {
    return ((e = pt(7, e, r, t)), (e.lanes = n), e);
  }
  function Kl(e, t, n, r) {
    return ((e = pt(22, e, r, t)), (e.elementType = oe), (e.lanes = n), (e.stateNode = { isHidden: !1 }), e);
  }
  function Xo(e, t, n) {
    return ((e = pt(6, e, null, t)), (e.lanes = n), e);
  }
  function Jo(e, t, n) {
    return (
      (t = pt(4, e.children !== null ? e.children : [], e.key, t)),
      (t.lanes = n),
      (t.stateNode = { containerInfo: e.containerInfo, pendingChildren: null, implementation: e.implementation }),
      t
    );
  }
  function lp(e, t, n, r, l) {
    ((this.tag = t),
      (this.containerInfo = e),
      (this.finishedWork = this.pingCache = this.current = this.pendingChildren = null),
      (this.timeoutHandle = -1),
      (this.callbackNode = this.pendingContext = this.context = null),
      (this.callbackPriority = 0),
      (this.eventTimes = ki(0)),
      (this.expirationTimes = ki(-1)),
      (this.entangledLanes =
        this.finishedLanes =
        this.mutableReadLanes =
        this.expiredLanes =
        this.pingedLanes =
        this.suspendedLanes =
        this.pendingLanes =
          0),
      (this.entanglements = ki(0)),
      (this.identifierPrefix = r),
      (this.onRecoverableError = l),
      (this.mutableSourceEagerHydrationData = null));
  }
  function Zo(e, t, n, r, l, o, a, v, g) {
    return (
      (e = new lp(e, t, n, v, g)),
      t === 1 ? ((t = 1), o === !0 && (t |= 8)) : (t = 0),
      (o = pt(3, null, null, t)),
      (e.current = o),
      (o.stateNode = e),
      (o.memoizedState = {
        element: r,
        isDehydrated: n,
        cache: null,
        transitions: null,
        pendingSuspenseBoundaries: null,
      }),
      co(o),
      e
    );
  }
  function ip(e, t, n) {
    var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
    return { $$typeof: he, key: r == null ? null : "" + r, children: e, containerInfo: t, implementation: n };
  }
  function pc(e) {
    if (!e) return Jt;
    e = e._reactInternals;
    e: {
      if (dn(e) !== e || e.tag !== 1) throw Error(s(170));
      var t = e;
      do {
        switch (t.tag) {
          case 3:
            t = t.stateNode.context;
            break e;
          case 1:
            if (Je(t.type)) {
              t = t.stateNode.__reactInternalMemoizedMergedChildContext;
              break e;
            }
        }
        t = t.return;
      } while (t !== null);
      throw Error(s(171));
    }
    if (e.tag === 1) {
      var n = e.type;
      if (Je(n)) return Bu(e, n, t);
    }
    return t;
  }
  function hc(e, t, n, r, l, o, a, v, g) {
    return (
      (e = Zo(n, r, !0, e, l, o, a, v, g)),
      (e.context = pc(null)),
      (n = e.current),
      (r = Ye()),
      (l = ln(n)),
      (o = zt(r, l)),
      (o.callback = t ?? null),
      en(n, o, l),
      (e.current.lanes = l),
      ir(e, l, r),
      et(e, r),
      e
    );
  }
  function ql(e, t, n, r) {
    var l = t.current,
      o = Ye(),
      a = ln(l);
    return (
      (n = pc(n)),
      t.context === null ? (t.context = n) : (t.pendingContext = n),
      (t = zt(o, a)),
      (t.payload = { element: e }),
      (r = r === void 0 ? null : r),
      r !== null && (t.callback = r),
      (e = en(l, t, a)),
      e !== null && (St(e, l, a, o), El(e, l, a)),
      a
    );
  }
  function Yl(e) {
    if (((e = e.current), !e.child)) return null;
    switch (e.child.tag) {
      case 5:
        return e.child.stateNode;
      default:
        return e.child.stateNode;
    }
  }
  function mc(e, t) {
    if (((e = e.memoizedState), e !== null && e.dehydrated !== null)) {
      var n = e.retryLane;
      e.retryLane = n !== 0 && n < t ? n : t;
    }
  }
  function bo(e, t) {
    (mc(e, t), (e = e.alternate) && mc(e, t));
  }
  function op() {
    return null;
  }
  var vc =
    typeof reportError == "function"
      ? reportError
      : function (e) {
          console.error(e);
        };
  function es(e) {
    this._internalRoot = e;
  }
  ((Gl.prototype.render = es.prototype.render =
    function (e) {
      var t = this._internalRoot;
      if (t === null) throw Error(s(409));
      ql(e, t, null, null);
    }),
    (Gl.prototype.unmount = es.prototype.unmount =
      function () {
        var e = this._internalRoot;
        if (e !== null) {
          this._internalRoot = null;
          var t = e.containerInfo;
          (xn(function () {
            ql(null, e, null, null);
          }),
            (t[Tt] = null));
        }
      }));
  function Gl(e) {
    this._internalRoot = e;
  }
  Gl.prototype.unstable_scheduleHydration = function (e) {
    if (e) {
      var t = bs();
      e = { blockedOn: null, target: e, priority: t };
      for (var n = 0; n < Kt.length && t !== 0 && t < Kt[n].priority; n++);
      (Kt.splice(n, 0, e), n === 0 && nu(e));
    }
  };
  function ts(e) {
    return !(!e || (e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11));
  }
  function Xl(e) {
    return !(
      !e ||
      (e.nodeType !== 1 &&
        e.nodeType !== 9 &&
        e.nodeType !== 11 &&
        (e.nodeType !== 8 || e.nodeValue !== " react-mount-point-unstable "))
    );
  }
  function yc() {}
  function sp(e, t, n, r, l) {
    if (l) {
      if (typeof r == "function") {
        var o = r;
        r = function () {
          var N = Yl(a);
          o.call(N);
        };
      }
      var a = hc(t, r, e, 0, null, !1, !1, "", yc);
      return ((e._reactRootContainer = a), (e[Tt] = a.current), _r(e.nodeType === 8 ? e.parentNode : e), xn(), a);
    }
    for (; (l = e.lastChild); ) e.removeChild(l);
    if (typeof r == "function") {
      var v = r;
      r = function () {
        var N = Yl(g);
        v.call(N);
      };
    }
    var g = Zo(e, 0, !1, null, null, !1, !1, "", yc);
    return (
      (e._reactRootContainer = g),
      (e[Tt] = g.current),
      _r(e.nodeType === 8 ? e.parentNode : e),
      xn(function () {
        ql(t, g, n, r);
      }),
      g
    );
  }
  function Jl(e, t, n, r, l) {
    var o = n._reactRootContainer;
    if (o) {
      var a = o;
      if (typeof l == "function") {
        var v = l;
        l = function () {
          var g = Yl(a);
          v.call(g);
        };
      }
      ql(t, a, e, l);
    } else a = sp(n, t, e, l, r);
    return Yl(a);
  }
  ((Js = function (e) {
    switch (e.tag) {
      case 3:
        var t = e.stateNode;
        if (t.current.memoizedState.isDehydrated) {
          var n = lr(t.pendingLanes);
          n !== 0 && (Ei(t, n | 1), et(t, Pe()), (se & 6) === 0 && ((Yn = Pe() + 500), Zt()));
        }
        break;
      case 13:
        (xn(function () {
          var r = It(e, 1);
          if (r !== null) {
            var l = Ye();
            St(r, e, 1, l);
          }
        }),
          bo(e, 1));
    }
  }),
    (Ci = function (e) {
      if (e.tag === 13) {
        var t = It(e, 134217728);
        if (t !== null) {
          var n = Ye();
          St(t, e, 134217728, n);
        }
        bo(e, 134217728);
      }
    }),
    (Zs = function (e) {
      if (e.tag === 13) {
        var t = ln(e),
          n = It(e, t);
        if (n !== null) {
          var r = Ye();
          St(n, e, t, r);
        }
        bo(e, t);
      }
    }),
    (bs = function () {
      return pe;
    }),
    (eu = function (e, t) {
      var n = pe;
      try {
        return ((pe = e), t());
      } finally {
        pe = n;
      }
    }),
    (yi = function (e, t, n) {
      switch (t) {
        case "input":
          if ((ai(e, n), (t = n.name), n.type === "radio" && t != null)) {
            for (n = e; n.parentNode; ) n = n.parentNode;
            for (
              n = n.querySelectorAll("input[name=" + JSON.stringify("" + t) + '][type="radio"]'), t = 0;
              t < n.length;
              t++
            ) {
              var r = n[t];
              if (r !== e && r.form === e.form) {
                var l = hl(r);
                if (!l) throw Error(s(90));
                (Es(r), ai(r, l));
              }
            }
          }
          break;
        case "textarea":
          Ps(e, n);
          break;
        case "select":
          ((t = n.value), t != null && Cn(e, !!n.multiple, t, !1));
      }
    }),
    (As = Ko),
    (Us = xn));
  var up = { usingClientEntryPoint: !1, Events: [Sr, In, hl, zs, Fs, Ko] },
    zr = { findFiberByHostInstance: pn, bundleType: 0, version: "18.3.1", rendererPackageName: "react-dom" },
    ap = {
      bundleType: zr.bundleType,
      version: zr.version,
      rendererPackageName: zr.rendererPackageName,
      rendererConfig: zr.rendererConfig,
      overrideHookState: null,
      overrideHookStateDeletePath: null,
      overrideHookStateRenamePath: null,
      overrideProps: null,
      overridePropsDeletePath: null,
      overridePropsRenamePath: null,
      setErrorHandler: null,
      setSuspenseHandler: null,
      scheduleUpdate: null,
      currentDispatcherRef: le.ReactCurrentDispatcher,
      findHostInstanceByFiber: function (e) {
        return ((e = Ws(e)), e === null ? null : e.stateNode);
      },
      findFiberByHostInstance: zr.findFiberByHostInstance || op,
      findHostInstancesForRefresh: null,
      scheduleRefresh: null,
      scheduleRoot: null,
      setRefreshHandler: null,
      getCurrentFiber: null,
      reconcilerVersion: "18.3.1-next-f1338f8080-20240426",
    };
  if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
    var Zl = __REACT_DEVTOOLS_GLOBAL_HOOK__;
    if (!Zl.isDisabled && Zl.supportsFiber)
      try {
        ((Gr = Zl.inject(ap)), (Et = Zl));
      } catch {}
  }
  return (
    (tt.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = up),
    (tt.createPortal = function (e, t) {
      var n = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
      if (!ts(t)) throw Error(s(200));
      return ip(e, t, null, n);
    }),
    (tt.createRoot = function (e, t) {
      if (!ts(e)) throw Error(s(299));
      var n = !1,
        r = "",
        l = vc;
      return (
        t != null &&
          (t.unstable_strictMode === !0 && (n = !0),
          t.identifierPrefix !== void 0 && (r = t.identifierPrefix),
          t.onRecoverableError !== void 0 && (l = t.onRecoverableError)),
        (t = Zo(e, 1, !1, null, null, n, !1, r, l)),
        (e[Tt] = t.current),
        _r(e.nodeType === 8 ? e.parentNode : e),
        new es(t)
      );
    }),
    (tt.findDOMNode = function (e) {
      if (e == null) return null;
      if (e.nodeType === 1) return e;
      var t = e._reactInternals;
      if (t === void 0)
        throw typeof e.render == "function" ? Error(s(188)) : ((e = Object.keys(e).join(",")), Error(s(268, e)));
      return ((e = Ws(t)), (e = e === null ? null : e.stateNode), e);
    }),
    (tt.flushSync = function (e) {
      return xn(e);
    }),
    (tt.hydrate = function (e, t, n) {
      if (!Xl(t)) throw Error(s(200));
      return Jl(null, e, t, !0, n);
    }),
    (tt.hydrateRoot = function (e, t, n) {
      if (!ts(e)) throw Error(s(405));
      var r = (n != null && n.hydratedSources) || null,
        l = !1,
        o = "",
        a = vc;
      if (
        (n != null &&
          (n.unstable_strictMode === !0 && (l = !0),
          n.identifierPrefix !== void 0 && (o = n.identifierPrefix),
          n.onRecoverableError !== void 0 && (a = n.onRecoverableError)),
        (t = hc(t, null, e, 1, n ?? null, l, !1, o, a)),
        (e[Tt] = t.current),
        _r(e),
        r)
      )
        for (e = 0; e < r.length; e++)
          ((n = r[e]),
            (l = n._getVersion),
            (l = l(n._source)),
            t.mutableSourceEagerHydrationData == null
              ? (t.mutableSourceEagerHydrationData = [n, l])
              : t.mutableSourceEagerHydrationData.push(n, l));
      return new Gl(t);
    }),
    (tt.render = function (e, t, n) {
      if (!Xl(t)) throw Error(s(200));
      return Jl(null, e, t, !1, n);
    }),
    (tt.unmountComponentAtNode = function (e) {
      if (!Xl(e)) throw Error(s(40));
      return e._reactRootContainer
        ? (xn(function () {
            Jl(null, null, e, !1, function () {
              ((e._reactRootContainer = null), (e[Tt] = null));
            });
          }),
          !0)
        : !1;
    }),
    (tt.unstable_batchedUpdates = Ko),
    (tt.unstable_renderSubtreeIntoContainer = function (e, t, n, r) {
      if (!Xl(n)) throw Error(s(200));
      if (e == null || e._reactInternals === void 0) throw Error(s(38));
      return Jl(e, t, n, !1, r);
    }),
    (tt.version = "18.3.1-next-f1338f8080-20240426"),
    tt
  );
}
var Cc;
function wp() {
  if (Cc) return ls.exports;
  Cc = 1;
  function i() {
    if (!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function"))
      try {
        __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(i);
      } catch (u) {
        console.error(u);
      }
  }
  return (i(), (ls.exports = _p()), ls.exports);
}
var Nc;
function xp() {
  if (Nc) return bl;
  Nc = 1;
  var i = wp();
  return ((bl.createRoot = i.createRoot), (bl.hydrateRoot = i.hydrateRoot), bl);
}
var Sp = xp();
const kp = Ac(Sp);
/**
 * react-router v7.11.0
 *
 * Copyright (c) Remix Software Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE.md file in the root directory of this source tree.
 *
 * @license MIT
 */ var Rc = "popstate";
function Ep(i = {}) {
  function u(c, f) {
    let { pathname: d, search: h, hash: y } = c.location;
    return ds(
      "",
      { pathname: d, search: h, hash: y },
      (f.state && f.state.usr) || null,
      (f.state && f.state.key) || "default"
    );
  }
  function s(c, f) {
    return typeof f == "string" ? f : Ur(f);
  }
  return Np(u, s, null, i);
}
function Ne(i, u) {
  if (i === !1 || i === null || typeof i > "u") throw new Error(u);
}
function ht(i, u) {
  if (!i) {
    typeof console < "u" && console.warn(u);
    try {
      throw new Error(u);
    } catch {}
  }
}
function Cp() {
  return Math.random().toString(36).substring(2, 10);
}
function jc(i, u) {
  return { usr: i.state, key: i.key, idx: u };
}
function ds(i, u, s = null, c) {
  return {
    pathname: typeof i == "string" ? i : i.pathname,
    search: "",
    hash: "",
    ...(typeof u == "string" ? Xn(u) : u),
    state: s,
    key: (u && u.key) || c || Cp(),
  };
}
function Ur({ pathname: i = "/", search: u = "", hash: s = "" }) {
  return (
    u && u !== "?" && (i += u.charAt(0) === "?" ? u : "?" + u),
    s && s !== "#" && (i += s.charAt(0) === "#" ? s : "#" + s),
    i
  );
}
function Xn(i) {
  let u = {};
  if (i) {
    let s = i.indexOf("#");
    s >= 0 && ((u.hash = i.substring(s)), (i = i.substring(0, s)));
    let c = i.indexOf("?");
    (c >= 0 && ((u.search = i.substring(c)), (i = i.substring(0, c))), i && (u.pathname = i));
  }
  return u;
}
function Np(i, u, s, c = {}) {
  let { window: f = document.defaultView, v5Compat: d = !1 } = c,
    h = f.history,
    y = "POP",
    m = null,
    w = S();
  w == null && ((w = 0), h.replaceState({ ...h.state, idx: w }, ""));
  function S() {
    return (h.state || { idx: null }).idx;
  }
  function R() {
    y = "POP";
    let D = S(),
      $ = D == null ? null : D - w;
    ((w = D), m && m({ action: y, location: z.location, delta: $ }));
  }
  function j(D, $) {
    y = "PUSH";
    let W = ds(z.location, D, $);
    w = S() + 1;
    let A = jc(W, w),
      le = z.createHref(W);
    try {
      h.pushState(A, "", le);
    } catch (ie) {
      if (ie instanceof DOMException && ie.name === "DataCloneError") throw ie;
      f.location.assign(le);
    }
    d && m && m({ action: y, location: z.location, delta: 1 });
  }
  function I(D, $) {
    y = "REPLACE";
    let W = ds(z.location, D, $);
    w = S();
    let A = jc(W, w),
      le = z.createHref(W);
    (h.replaceState(A, "", le), d && m && m({ action: y, location: z.location, delta: 0 }));
  }
  function F(D) {
    return Rp(D);
  }
  let z = {
    get action() {
      return y;
    },
    get location() {
      return i(f, h);
    },
    listen(D) {
      if (m) throw new Error("A history only accepts one active listener");
      return (
        f.addEventListener(Rc, R),
        (m = D),
        () => {
          (f.removeEventListener(Rc, R), (m = null));
        }
      );
    },
    createHref(D) {
      return u(f, D);
    },
    createURL: F,
    encodeLocation(D) {
      let $ = F(D);
      return { pathname: $.pathname, search: $.search, hash: $.hash };
    },
    push: j,
    replace: I,
    go(D) {
      return h.go(D);
    },
  };
  return z;
}
function Rp(i, u = !1) {
  let s = "http://localhost";
  (typeof window < "u" && (s = window.location.origin !== "null" ? window.location.origin : window.location.href),
    Ne(s, "No window.location.(origin|href) available to create URL"));
  let c = typeof i == "string" ? i : Ur(i);
  return ((c = c.replace(/ $/, "%20")), !u && c.startsWith("//") && (c = s + c), new URL(c, s));
}
function Uc(i, u, s = "/") {
  return jp(i, u, s, !1);
}
function jp(i, u, s, c) {
  let f = typeof u == "string" ? Xn(u) : u,
    d = Bt(f.pathname || "/", s);
  if (d == null) return null;
  let h = $c(i);
  Pp(h);
  let y = null;
  for (let m = 0; y == null && m < h.length; ++m) {
    let w = $p(d);
    y = Ap(h[m], w, c);
  }
  return y;
}
function $c(i, u = [], s = [], c = "", f = !1) {
  let d = (h, y, m = f, w) => {
    let S = {
      relativePath: w === void 0 ? h.path || "" : w,
      caseSensitive: h.caseSensitive === !0,
      childrenIndex: y,
      route: h,
    };
    if (S.relativePath.startsWith("/")) {
      if (!S.relativePath.startsWith(c) && m) return;
      (Ne(
        S.relativePath.startsWith(c),
        `Absolute route path "${S.relativePath}" nested under path "${c}" is not valid. An absolute child route path must start with the combined path of all its parent routes.`
      ),
        (S.relativePath = S.relativePath.slice(c.length)));
    }
    let R = $t([c, S.relativePath]),
      j = s.concat(S);
    (h.children &&
      h.children.length > 0 &&
      (Ne(
        h.index !== !0,
        `Index routes must not have child routes. Please remove all child routes from route path "${R}".`
      ),
      $c(h.children, u, j, R, m)),
      !(h.path == null && !h.index) && u.push({ path: R, score: zp(R, h.index), routesMeta: j }));
  };
  return (
    i.forEach((h, y) => {
      var m;
      if (h.path === "" || !((m = h.path) != null && m.includes("?"))) d(h, y);
      else for (let w of Bc(h.path)) d(h, y, !0, w);
    }),
    u
  );
}
function Bc(i) {
  let u = i.split("/");
  if (u.length === 0) return [];
  let [s, ...c] = u,
    f = s.endsWith("?"),
    d = s.replace(/\?$/, "");
  if (c.length === 0) return f ? [d, ""] : [d];
  let h = Bc(c.join("/")),
    y = [];
  return (
    y.push(...h.map((m) => (m === "" ? d : [d, m].join("/")))),
    f && y.push(...h),
    y.map((m) => (i.startsWith("/") && m === "" ? "/" : m))
  );
}
function Pp(i) {
  i.sort((u, s) =>
    u.score !== s.score
      ? s.score - u.score
      : Fp(
          u.routesMeta.map((c) => c.childrenIndex),
          s.routesMeta.map((c) => c.childrenIndex)
        )
  );
}
var Lp = /^:[\w-]+$/,
  Tp = 3,
  Op = 2,
  Mp = 1,
  Dp = 10,
  Ip = -2,
  Pc = (i) => i === "*";
function zp(i, u) {
  let s = i.split("/"),
    c = s.length;
  return (
    s.some(Pc) && (c += Ip),
    u && (c += Op),
    s.filter((f) => !Pc(f)).reduce((f, d) => f + (Lp.test(d) ? Tp : d === "" ? Mp : Dp), c)
  );
}
function Fp(i, u) {
  return i.length === u.length && i.slice(0, -1).every((c, f) => c === u[f]) ? i[i.length - 1] - u[u.length - 1] : 0;
}
function Ap(i, u, s = !1) {
  let { routesMeta: c } = i,
    f = {},
    d = "/",
    h = [];
  for (let y = 0; y < c.length; ++y) {
    let m = c[y],
      w = y === c.length - 1,
      S = d === "/" ? u : u.slice(d.length) || "/",
      R = ri({ path: m.relativePath, caseSensitive: m.caseSensitive, end: w }, S),
      j = m.route;
    if (
      (!R &&
        w &&
        s &&
        !c[c.length - 1].route.index &&
        (R = ri({ path: m.relativePath, caseSensitive: m.caseSensitive, end: !1 }, S)),
      !R)
    )
      return null;
    (Object.assign(f, R.params),
      h.push({ params: f, pathname: $t([d, R.pathname]), pathnameBase: Vp($t([d, R.pathnameBase])), route: j }),
      R.pathnameBase !== "/" && (d = $t([d, R.pathnameBase])));
  }
  return h;
}
function ri(i, u) {
  typeof i == "string" && (i = { path: i, caseSensitive: !1, end: !0 });
  let [s, c] = Up(i.path, i.caseSensitive, i.end),
    f = u.match(s);
  if (!f) return null;
  let d = f[0],
    h = d.replace(/(.)\/+$/, "$1"),
    y = f.slice(1);
  return {
    params: c.reduce((w, { paramName: S, isOptional: R }, j) => {
      if (S === "*") {
        let F = y[j] || "";
        h = d.slice(0, d.length - F.length).replace(/(.)\/+$/, "$1");
      }
      const I = y[j];
      return (R && !I ? (w[S] = void 0) : (w[S] = (I || "").replace(/%2F/g, "/")), w);
    }, {}),
    pathname: d,
    pathnameBase: h,
    pattern: i,
  };
}
function Up(i, u = !1, s = !0) {
  ht(
    i === "*" || !i.endsWith("*") || i.endsWith("/*"),
    `Route path "${i}" will be treated as if it were "${i.replace(/\*$/, "/*")}" because the \`*\` character must always follow a \`/\` in the pattern. To get rid of this warning, please change the route path to "${i.replace(/\*$/, "/*")}".`
  );
  let c = [],
    f =
      "^" +
      i
        .replace(/\/*\*?$/, "")
        .replace(/^\/*/, "/")
        .replace(/[\\.*+^${}|()[\]]/g, "\\$&")
        .replace(
          /\/:([\w-]+)(\?)?/g,
          (h, y, m) => (c.push({ paramName: y, isOptional: m != null }), m ? "/?([^\\/]+)?" : "/([^\\/]+)")
        )
        .replace(/\/([\w-]+)\?(\/|$)/g, "(/$1)?$2");
  return (
    i.endsWith("*")
      ? (c.push({ paramName: "*" }), (f += i === "*" || i === "/*" ? "(.*)$" : "(?:\\/(.+)|\\/*)$"))
      : s
        ? (f += "\\/*$")
        : i !== "" && i !== "/" && (f += "(?:(?=\\/|$))"),
    [new RegExp(f, u ? void 0 : "i"), c]
  );
}
function $p(i) {
  try {
    return i
      .split("/")
      .map((u) => decodeURIComponent(u).replace(/\//g, "%2F"))
      .join("/");
  } catch (u) {
    return (
      ht(
        !1,
        `The URL path "${i}" could not be decoded because it is a malformed URL segment. This is probably due to a bad percent encoding (${u}).`
      ),
      i
    );
  }
}
function Bt(i, u) {
  if (u === "/") return i;
  if (!i.toLowerCase().startsWith(u.toLowerCase())) return null;
  let s = u.endsWith("/") ? u.length - 1 : u.length,
    c = i.charAt(s);
  return c && c !== "/" ? null : i.slice(s) || "/";
}
var Hc = /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i,
  Bp = (i) => Hc.test(i);
function Hp(i, u = "/") {
  let { pathname: s, search: c = "", hash: f = "" } = typeof i == "string" ? Xn(i) : i,
    d;
  if (s)
    if (Bp(s)) d = s;
    else {
      if (s.includes("//")) {
        let h = s;
        ((s = s.replace(/\/\/+/g, "/")),
          ht(!1, `Pathnames cannot have embedded double slashes - normalizing ${h} -> ${s}`));
      }
      s.startsWith("/") ? (d = Lc(s.substring(1), "/")) : (d = Lc(s, u));
    }
  else d = u;
  return { pathname: d, search: Qp(c), hash: Kp(f) };
}
function Lc(i, u) {
  let s = u.replace(/\/+$/, "").split("/");
  return (
    i.split("/").forEach((f) => {
      f === ".." ? s.length > 1 && s.pop() : f !== "." && s.push(f);
    }),
    s.length > 1 ? s.join("/") : "/"
  );
}
function ss(i, u, s, c) {
  return `Cannot include a '${i}' character in a manually specified \`to.${u}\` field [${JSON.stringify(c)}].  Please separate it out to the \`to.${s}\` field. Alternatively you may provide the full path as a string in <Link to="..."> and the router will parse it for you.`;
}
function Wp(i) {
  return i.filter((u, s) => s === 0 || (u.route.path && u.route.path.length > 0));
}
function Wc(i) {
  let u = Wp(i);
  return u.map((s, c) => (c === u.length - 1 ? s.pathname : s.pathnameBase));
}
function Vc(i, u, s, c = !1) {
  let f;
  typeof i == "string"
    ? (f = Xn(i))
    : ((f = { ...i }),
      Ne(!f.pathname || !f.pathname.includes("?"), ss("?", "pathname", "search", f)),
      Ne(!f.pathname || !f.pathname.includes("#"), ss("#", "pathname", "hash", f)),
      Ne(!f.search || !f.search.includes("#"), ss("#", "search", "hash", f)));
  let d = i === "" || f.pathname === "",
    h = d ? "/" : f.pathname,
    y;
  if (h == null) y = s;
  else {
    let R = u.length - 1;
    if (!c && h.startsWith("..")) {
      let j = h.split("/");
      for (; j[0] === ".."; ) (j.shift(), (R -= 1));
      f.pathname = j.join("/");
    }
    y = R >= 0 ? u[R] : "/";
  }
  let m = Hp(f, y),
    w = h && h !== "/" && h.endsWith("/"),
    S = (d || h === ".") && s.endsWith("/");
  return (!m.pathname.endsWith("/") && (w || S) && (m.pathname += "/"), m);
}
var $t = (i) => i.join("/").replace(/\/\/+/g, "/"),
  Vp = (i) => i.replace(/\/+$/, "").replace(/^\/*/, "/"),
  Qp = (i) => (!i || i === "?" ? "" : i.startsWith("?") ? i : "?" + i),
  Kp = (i) => (!i || i === "#" ? "" : i.startsWith("#") ? i : "#" + i),
  qp = class {
    constructor(i, u, s, c = !1) {
      ((this.status = i),
        (this.statusText = u || ""),
        (this.internal = c),
        s instanceof Error ? ((this.data = s.toString()), (this.error = s)) : (this.data = s));
    }
  };
function Yp(i) {
  return (
    i != null &&
    typeof i.status == "number" &&
    typeof i.statusText == "string" &&
    typeof i.internal == "boolean" &&
    "data" in i
  );
}
function Gp(i) {
  return (
    i
      .map((u) => u.route.path)
      .filter(Boolean)
      .join("/")
      .replace(/\/\/*/g, "/") || "/"
  );
}
var Qc = typeof window < "u" && typeof window.document < "u" && typeof window.document.createElement < "u";
function Kc(i, u) {
  let s = i;
  if (typeof s != "string" || !Hc.test(s)) return { absoluteURL: void 0, isExternal: !1, to: s };
  let c = s,
    f = !1;
  if (Qc)
    try {
      let d = new URL(window.location.href),
        h = s.startsWith("//") ? new URL(d.protocol + s) : new URL(s),
        y = Bt(h.pathname, u);
      h.origin === d.origin && y != null ? (s = y + h.search + h.hash) : (f = !0);
    } catch {
      ht(
        !1,
        `<Link to="${s}"> contains an invalid URL which will probably break when clicked - please update to a valid URL path.`
      );
    }
  return { absoluteURL: c, isExternal: f, to: s };
}
Object.getOwnPropertyNames(Object.prototype).sort().join("\0");
var qc = ["POST", "PUT", "PATCH", "DELETE"];
new Set(qc);
var Xp = ["GET", ...qc];
new Set(Xp);
var Jn = C.createContext(null);
Jn.displayName = "DataRouter";
var oi = C.createContext(null);
oi.displayName = "DataRouterState";
var Jp = C.createContext(!1),
  Yc = C.createContext({ isTransitioning: !1 });
Yc.displayName = "ViewTransition";
var Zp = C.createContext(new Map());
Zp.displayName = "Fetchers";
var bp = C.createContext(null);
bp.displayName = "Await";
var mt = C.createContext(null);
mt.displayName = "Navigation";
var $r = C.createContext(null);
$r.displayName = "Location";
var Ht = C.createContext({ outlet: null, matches: [], isDataRoute: !1 });
Ht.displayName = "Route";
var ys = C.createContext(null);
ys.displayName = "RouteError";
var Gc = "REACT_ROUTER_ERROR",
  eh = "REDIRECT",
  th = "ROUTE_ERROR_RESPONSE";
function nh(i) {
  if (i.startsWith(`${Gc}:${eh}:{`))
    try {
      let u = JSON.parse(i.slice(28));
      if (
        typeof u == "object" &&
        u &&
        typeof u.status == "number" &&
        typeof u.statusText == "string" &&
        typeof u.location == "string" &&
        typeof u.reloadDocument == "boolean" &&
        typeof u.replace == "boolean"
      )
        return u;
    } catch {}
}
function rh(i) {
  if (i.startsWith(`${Gc}:${th}:{`))
    try {
      let u = JSON.parse(i.slice(40));
      if (typeof u == "object" && u && typeof u.status == "number" && typeof u.statusText == "string")
        return new qp(u.status, u.statusText, u.data);
    } catch {}
}
function lh(i, { relative: u } = {}) {
  Ne(Br(), "useHref() may be used only in the context of a <Router> component.");
  let { basename: s, navigator: c } = C.useContext(mt),
    { hash: f, pathname: d, search: h } = Hr(i, { relative: u }),
    y = d;
  return (s !== "/" && (y = d === "/" ? s : $t([s, d])), c.createHref({ pathname: y, search: h, hash: f }));
}
function Br() {
  return C.useContext($r) != null;
}
function cn() {
  return (
    Ne(Br(), "useLocation() may be used only in the context of a <Router> component."),
    C.useContext($r).location
  );
}
var Xc = "You should call navigate() in a React.useEffect(), not when your component is first rendered.";
function Jc(i) {
  C.useContext(mt).static || C.useLayoutEffect(i);
}
function Zc() {
  let { isDataRoute: i } = C.useContext(Ht);
  return i ? yh() : ih();
}
function ih() {
  Ne(Br(), "useNavigate() may be used only in the context of a <Router> component.");
  let i = C.useContext(Jn),
    { basename: u, navigator: s } = C.useContext(mt),
    { matches: c } = C.useContext(Ht),
    { pathname: f } = cn(),
    d = JSON.stringify(Wc(c)),
    h = C.useRef(!1);
  return (
    Jc(() => {
      h.current = !0;
    }),
    C.useCallback(
      (m, w = {}) => {
        if ((ht(h.current, Xc), !h.current)) return;
        if (typeof m == "number") {
          s.go(m);
          return;
        }
        let S = Vc(m, JSON.parse(d), f, w.relative === "path");
        (i == null && u !== "/" && (S.pathname = S.pathname === "/" ? u : $t([u, S.pathname])),
          (w.replace ? s.replace : s.push)(S, w.state, w));
      },
      [u, s, d, f, i]
    )
  );
}
C.createContext(null);
function Hr(i, { relative: u } = {}) {
  let { matches: s } = C.useContext(Ht),
    { pathname: c } = cn(),
    f = JSON.stringify(Wc(s));
  return C.useMemo(() => Vc(i, JSON.parse(f), c, u === "path"), [i, f, c, u]);
}
function oh(i, u) {
  return bc(i, u);
}
function bc(i, u, s, c, f) {
  var W;
  Ne(Br(), "useRoutes() may be used only in the context of a <Router> component.");
  let { navigator: d } = C.useContext(mt),
    { matches: h } = C.useContext(Ht),
    y = h[h.length - 1],
    m = y ? y.params : {},
    w = y ? y.pathname : "/",
    S = y ? y.pathnameBase : "/",
    R = y && y.route;
  {
    let A = (R && R.path) || "";
    tf(
      w,
      !R || A.endsWith("*") || A.endsWith("*?"),
      `You rendered descendant <Routes> (or called \`useRoutes()\`) at "${w}" (under <Route path="${A}">) but the parent route path has no trailing "*". This means if you navigate deeper, the parent won't match anymore and therefore the child routes will never render.

Please change the parent <Route path="${A}"> to <Route path="${A === "/" ? "*" : `${A}/*`}">.`
    );
  }
  let j = cn(),
    I;
  if (u) {
    let A = typeof u == "string" ? Xn(u) : u;
    (Ne(
      S === "/" || ((W = A.pathname) == null ? void 0 : W.startsWith(S)),
      `When overriding the location using \`<Routes location>\` or \`useRoutes(routes, location)\`, the location pathname must begin with the portion of the URL pathname that was matched by all parent routes. The current pathname base is "${S}" but pathname "${A.pathname}" was given in the \`location\` prop.`
    ),
      (I = A));
  } else I = j;
  let F = I.pathname || "/",
    z = F;
  if (S !== "/") {
    let A = S.replace(/^\//, "").split("/");
    z = "/" + F.replace(/^\//, "").split("/").slice(A.length).join("/");
  }
  let D = Uc(i, { pathname: z });
  (ht(R || D != null, `No routes matched location "${I.pathname}${I.search}${I.hash}" `),
    ht(
      D == null ||
        D[D.length - 1].route.element !== void 0 ||
        D[D.length - 1].route.Component !== void 0 ||
        D[D.length - 1].route.lazy !== void 0,
      `Matched leaf route at location "${I.pathname}${I.search}${I.hash}" does not have an element or Component. This means it will render an <Outlet /> with a null value by default resulting in an "empty" page.`
    ));
  let $ = fh(
    D &&
      D.map((A) =>
        Object.assign({}, A, {
          params: Object.assign({}, m, A.params),
          pathname: $t([
            S,
            d.encodeLocation
              ? d.encodeLocation(A.pathname.replace(/\?/g, "%3F").replace(/#/g, "%23")).pathname
              : A.pathname,
          ]),
          pathnameBase:
            A.pathnameBase === "/"
              ? S
              : $t([
                  S,
                  d.encodeLocation
                    ? d.encodeLocation(A.pathnameBase.replace(/\?/g, "%3F").replace(/#/g, "%23")).pathname
                    : A.pathnameBase,
                ]),
        })
      ),
    h,
    s,
    c,
    f
  );
  return u && $
    ? C.createElement(
        $r.Provider,
        {
          value: {
            location: { pathname: "/", search: "", hash: "", state: null, key: "default", ...I },
            navigationType: "POP",
          },
        },
        $
      )
    : $;
}
function sh() {
  let i = vh(),
    u = Yp(i) ? `${i.status} ${i.statusText}` : i instanceof Error ? i.message : JSON.stringify(i),
    s = i instanceof Error ? i.stack : null,
    c = "rgba(200,200,200, 0.5)",
    f = { padding: "0.5rem", backgroundColor: c },
    d = { padding: "2px 4px", backgroundColor: c },
    h = null;
  return (
    console.error("Error handled by React Router default ErrorBoundary:", i),
    (h = C.createElement(
      C.Fragment,
      null,
      C.createElement("p", null, "💿 Hey developer 👋"),
      C.createElement(
        "p",
        null,
        "You can provide a way better UX than this when your app throws errors by providing your own ",
        C.createElement("code", { style: d }, "ErrorBoundary"),
        " or",
        " ",
        C.createElement("code", { style: d }, "errorElement"),
        " prop on your route."
      )
    )),
    C.createElement(
      C.Fragment,
      null,
      C.createElement("h2", null, "Unexpected Application Error!"),
      C.createElement("h3", { style: { fontStyle: "italic" } }, u),
      s ? C.createElement("pre", { style: f }, s) : null,
      h
    )
  );
}
var uh = C.createElement(sh, null),
  ef = class extends C.Component {
    constructor(i) {
      (super(i), (this.state = { location: i.location, revalidation: i.revalidation, error: i.error }));
    }
    static getDerivedStateFromError(i) {
      return { error: i };
    }
    static getDerivedStateFromProps(i, u) {
      return u.location !== i.location || (u.revalidation !== "idle" && i.revalidation === "idle")
        ? { error: i.error, location: i.location, revalidation: i.revalidation }
        : {
            error: i.error !== void 0 ? i.error : u.error,
            location: u.location,
            revalidation: i.revalidation || u.revalidation,
          };
    }
    componentDidCatch(i, u) {
      this.props.onError
        ? this.props.onError(i, u)
        : console.error("React Router caught the following error during render", i);
    }
    render() {
      let i = this.state.error;
      if (this.context && typeof i == "object" && i && "digest" in i && typeof i.digest == "string") {
        const s = rh(i.digest);
        s && (i = s);
      }
      let u =
        i !== void 0
          ? C.createElement(
              Ht.Provider,
              { value: this.props.routeContext },
              C.createElement(ys.Provider, { value: i, children: this.props.component })
            )
          : this.props.children;
      return this.context ? C.createElement(ah, { error: i }, u) : u;
    }
  };
ef.contextType = Jp;
var us = new WeakMap();
function ah({ children: i, error: u }) {
  let { basename: s } = C.useContext(mt);
  if (typeof u == "object" && u && "digest" in u && typeof u.digest == "string") {
    let c = nh(u.digest);
    if (c) {
      let f = us.get(u);
      if (f) throw f;
      let d = Kc(c.location, s);
      if (Qc && !us.get(u))
        if (d.isExternal || c.reloadDocument) window.location.href = d.absoluteURL || d.to;
        else {
          const h = Promise.resolve().then(() => window.__reactRouterDataRouter.navigate(d.to, { replace: c.replace }));
          throw (us.set(u, h), h);
        }
      return C.createElement("meta", { httpEquiv: "refresh", content: `0;url=${d.absoluteURL || d.to}` });
    }
  }
  return i;
}
function ch({ routeContext: i, match: u, children: s }) {
  let c = C.useContext(Jn);
  return (
    c &&
      c.static &&
      c.staticContext &&
      (u.route.errorElement || u.route.ErrorBoundary) &&
      (c.staticContext._deepestRenderedBoundaryId = u.route.id),
    C.createElement(Ht.Provider, { value: i }, s)
  );
}
function fh(i, u = [], s = null, c = null, f = null) {
  if (i == null) {
    if (!s) return null;
    if (s.errors) i = s.matches;
    else if (u.length === 0 && !s.initialized && s.matches.length > 0) i = s.matches;
    else return null;
  }
  let d = i,
    h = s == null ? void 0 : s.errors;
  if (h != null) {
    let S = d.findIndex((R) => R.route.id && (h == null ? void 0 : h[R.route.id]) !== void 0);
    (Ne(S >= 0, `Could not find a matching route for errors on route IDs: ${Object.keys(h).join(",")}`),
      (d = d.slice(0, Math.min(d.length, S + 1))));
  }
  let y = !1,
    m = -1;
  if (s)
    for (let S = 0; S < d.length; S++) {
      let R = d[S];
      if (((R.route.HydrateFallback || R.route.hydrateFallbackElement) && (m = S), R.route.id)) {
        let { loaderData: j, errors: I } = s,
          F = R.route.loader && !j.hasOwnProperty(R.route.id) && (!I || I[R.route.id] === void 0);
        if (R.route.lazy || F) {
          ((y = !0), m >= 0 ? (d = d.slice(0, m + 1)) : (d = [d[0]]));
          break;
        }
      }
    }
  let w =
    s && c
      ? (S, R) => {
          var j, I;
          c(S, {
            location: s.location,
            params: ((I = (j = s.matches) == null ? void 0 : j[0]) == null ? void 0 : I.params) ?? {},
            unstable_pattern: Gp(s.matches),
            errorInfo: R,
          });
        }
      : void 0;
  return d.reduceRight((S, R, j) => {
    let I,
      F = !1,
      z = null,
      D = null;
    s &&
      ((I = h && R.route.id ? h[R.route.id] : void 0),
      (z = R.route.errorElement || uh),
      y &&
        (m < 0 && j === 0
          ? (tf("route-fallback", !1, "No `HydrateFallback` element provided to render during initial hydration"),
            (F = !0),
            (D = null))
          : m === j && ((F = !0), (D = R.route.hydrateFallbackElement || null))));
    let $ = u.concat(d.slice(0, j + 1)),
      W = () => {
        let A;
        return (
          I
            ? (A = z)
            : F
              ? (A = D)
              : R.route.Component
                ? (A = C.createElement(R.route.Component, null))
                : R.route.element
                  ? (A = R.route.element)
                  : (A = S),
          C.createElement(ch, {
            match: R,
            routeContext: { outlet: S, matches: $, isDataRoute: s != null },
            children: A,
          })
        );
      };
    return s && (R.route.ErrorBoundary || R.route.errorElement || j === 0)
      ? C.createElement(ef, {
          location: s.location,
          revalidation: s.revalidation,
          component: z,
          error: I,
          children: W(),
          routeContext: { outlet: null, matches: $, isDataRoute: !0 },
          onError: w,
        })
      : W();
  }, null);
}
function gs(i) {
  return `${i} must be used within a data router.  See https://reactrouter.com/en/main/routers/picking-a-router.`;
}
function dh(i) {
  let u = C.useContext(Jn);
  return (Ne(u, gs(i)), u);
}
function ph(i) {
  let u = C.useContext(oi);
  return (Ne(u, gs(i)), u);
}
function hh(i) {
  let u = C.useContext(Ht);
  return (Ne(u, gs(i)), u);
}
function _s(i) {
  let u = hh(i),
    s = u.matches[u.matches.length - 1];
  return (Ne(s.route.id, `${i} can only be used on routes that contain a unique "id"`), s.route.id);
}
function mh() {
  return _s("useRouteId");
}
function vh() {
  var c;
  let i = C.useContext(ys),
    u = ph("useRouteError"),
    s = _s("useRouteError");
  return i !== void 0 ? i : (c = u.errors) == null ? void 0 : c[s];
}
function yh() {
  let { router: i } = dh("useNavigate"),
    u = _s("useNavigate"),
    s = C.useRef(!1);
  return (
    Jc(() => {
      s.current = !0;
    }),
    C.useCallback(
      async (f, d = {}) => {
        (ht(s.current, Xc),
          s.current && (typeof f == "number" ? await i.navigate(f) : await i.navigate(f, { fromRouteId: u, ...d })));
      },
      [i, u]
    )
  );
}
var Tc = {};
function tf(i, u, s) {
  !u && !Tc[i] && ((Tc[i] = !0), ht(!1, s));
}
C.memo(gh);
function gh({ routes: i, future: u, state: s, onError: c }) {
  return bc(i, void 0, s, c, u);
}
function ps(i) {
  Ne(
    !1,
    "A <Route> is only ever to be used as the child of <Routes> element, never rendered directly. Please wrap your <Route> in a <Routes>."
  );
}
function _h({
  basename: i = "/",
  children: u = null,
  location: s,
  navigationType: c = "POP",
  navigator: f,
  static: d = !1,
  unstable_useTransitions: h,
}) {
  Ne(!Br(), "You cannot render a <Router> inside another <Router>. You should never have more than one in your app.");
  let y = i.replace(/^\/*/, "/"),
    m = C.useMemo(
      () => ({ basename: y, navigator: f, static: d, unstable_useTransitions: h, future: {} }),
      [y, f, d, h]
    );
  typeof s == "string" && (s = Xn(s));
  let { pathname: w = "/", search: S = "", hash: R = "", state: j = null, key: I = "default" } = s,
    F = C.useMemo(() => {
      let z = Bt(w, y);
      return z == null ? null : { location: { pathname: z, search: S, hash: R, state: j, key: I }, navigationType: c };
    }, [y, w, S, R, j, I, c]);
  return (
    ht(
      F != null,
      `<Router basename="${y}"> is not able to match the URL "${w}${S}${R}" because it does not start with the basename, so the <Router> won't render anything.`
    ),
    F == null
      ? null
      : C.createElement(mt.Provider, { value: m }, C.createElement($r.Provider, { children: u, value: F }))
  );
}
function wh({ children: i, location: u }) {
  return oh(hs(i), u);
}
function hs(i, u = []) {
  let s = [];
  return (
    C.Children.forEach(i, (c, f) => {
      if (!C.isValidElement(c)) return;
      let d = [...u, f];
      if (c.type === C.Fragment) {
        s.push.apply(s, hs(c.props.children, d));
        return;
      }
      (Ne(
        c.type === ps,
        `[${typeof c.type == "string" ? c.type : c.type.name}] is not a <Route> component. All component children of <Routes> must be a <Route> or <React.Fragment>`
      ),
        Ne(!c.props.index || !c.props.children, "An index route cannot have child routes."));
      let h = {
        id: c.props.id || d.join("-"),
        caseSensitive: c.props.caseSensitive,
        element: c.props.element,
        Component: c.props.Component,
        index: c.props.index,
        path: c.props.path,
        middleware: c.props.middleware,
        loader: c.props.loader,
        action: c.props.action,
        hydrateFallbackElement: c.props.hydrateFallbackElement,
        HydrateFallback: c.props.HydrateFallback,
        errorElement: c.props.errorElement,
        ErrorBoundary: c.props.ErrorBoundary,
        hasErrorBoundary:
          c.props.hasErrorBoundary === !0 || c.props.ErrorBoundary != null || c.props.errorElement != null,
        shouldRevalidate: c.props.shouldRevalidate,
        handle: c.props.handle,
        lazy: c.props.lazy,
      };
      (c.props.children && (h.children = hs(c.props.children, d)), s.push(h));
    }),
    s
  );
}
var ti = "get",
  ni = "application/x-www-form-urlencoded";
function si(i) {
  return typeof HTMLElement < "u" && i instanceof HTMLElement;
}
function xh(i) {
  return si(i) && i.tagName.toLowerCase() === "button";
}
function Sh(i) {
  return si(i) && i.tagName.toLowerCase() === "form";
}
function kh(i) {
  return si(i) && i.tagName.toLowerCase() === "input";
}
function Eh(i) {
  return !!(i.metaKey || i.altKey || i.ctrlKey || i.shiftKey);
}
function Ch(i, u) {
  return i.button === 0 && (!u || u === "_self") && !Eh(i);
}
function ms(i = "") {
  return new URLSearchParams(
    typeof i == "string" || Array.isArray(i) || i instanceof URLSearchParams
      ? i
      : Object.keys(i).reduce((u, s) => {
          let c = i[s];
          return u.concat(Array.isArray(c) ? c.map((f) => [s, f]) : [[s, c]]);
        }, [])
  );
}
function Nh(i, u) {
  let s = ms(i);
  return (
    u &&
      u.forEach((c, f) => {
        s.has(f) ||
          u.getAll(f).forEach((d) => {
            s.append(f, d);
          });
      }),
    s
  );
}
var ei = null;
function Rh() {
  if (ei === null)
    try {
      (new FormData(document.createElement("form"), 0), (ei = !1));
    } catch {
      ei = !0;
    }
  return ei;
}
var jh = new Set(["application/x-www-form-urlencoded", "multipart/form-data", "text/plain"]);
function as(i) {
  return i != null && !jh.has(i)
    ? (ht(!1, `"${i}" is not a valid \`encType\` for \`<Form>\`/\`<fetcher.Form>\` and will default to "${ni}"`), null)
    : i;
}
function Ph(i, u) {
  let s, c, f, d, h;
  if (Sh(i)) {
    let y = i.getAttribute("action");
    ((c = y ? Bt(y, u) : null),
      (s = i.getAttribute("method") || ti),
      (f = as(i.getAttribute("enctype")) || ni),
      (d = new FormData(i)));
  } else if (xh(i) || (kh(i) && (i.type === "submit" || i.type === "image"))) {
    let y = i.form;
    if (y == null) throw new Error('Cannot submit a <button> or <input type="submit"> without a <form>');
    let m = i.getAttribute("formaction") || y.getAttribute("action");
    if (
      ((c = m ? Bt(m, u) : null),
      (s = i.getAttribute("formmethod") || y.getAttribute("method") || ti),
      (f = as(i.getAttribute("formenctype")) || as(y.getAttribute("enctype")) || ni),
      (d = new FormData(y, i)),
      !Rh())
    ) {
      let { name: w, type: S, value: R } = i;
      if (S === "image") {
        let j = w ? `${w}.` : "";
        (d.append(`${j}x`, "0"), d.append(`${j}y`, "0"));
      } else w && d.append(w, R);
    }
  } else {
    if (si(i)) throw new Error('Cannot submit element that is not <form>, <button>, or <input type="submit|image">');
    ((s = ti), (c = null), (f = ni), (h = i));
  }
  return (
    d && f === "text/plain" && ((h = d), (d = void 0)),
    { action: c, method: s.toLowerCase(), encType: f, formData: d, body: h }
  );
}
Object.getOwnPropertyNames(Object.prototype).sort().join("\0");
function ws(i, u) {
  if (i === !1 || i === null || typeof i > "u") throw new Error(u);
}
function Lh(i, u, s) {
  let c = typeof i == "string" ? new URL(i, typeof window > "u" ? "server://singlefetch/" : window.location.origin) : i;
  return (
    c.pathname === "/"
      ? (c.pathname = `_root.${s}`)
      : u && Bt(c.pathname, u) === "/"
        ? (c.pathname = `${u.replace(/\/$/, "")}/_root.${s}`)
        : (c.pathname = `${c.pathname.replace(/\/$/, "")}.${s}`),
    c
  );
}
async function Th(i, u) {
  if (i.id in u) return u[i.id];
  try {
    let s = await import(i.module);
    return ((u[i.id] = s), s);
  } catch (s) {
    return (
      console.error(`Error loading route module \`${i.module}\`, reloading page...`),
      console.error(s),
      window.__reactRouterContext && window.__reactRouterContext.isSpaMode,
      window.location.reload(),
      new Promise(() => {})
    );
  }
}
function Oh(i) {
  return i == null
    ? !1
    : i.href == null
      ? i.rel === "preload" && typeof i.imageSrcSet == "string" && typeof i.imageSizes == "string"
      : typeof i.rel == "string" && typeof i.href == "string";
}
async function Mh(i, u, s) {
  let c = await Promise.all(
    i.map(async (f) => {
      let d = u.routes[f.route.id];
      if (d) {
        let h = await Th(d, s);
        return h.links ? h.links() : [];
      }
      return [];
    })
  );
  return Fh(
    c
      .flat(1)
      .filter(Oh)
      .filter((f) => f.rel === "stylesheet" || f.rel === "preload")
      .map((f) => (f.rel === "stylesheet" ? { ...f, rel: "prefetch", as: "style" } : { ...f, rel: "prefetch" }))
  );
}
function Oc(i, u, s, c, f, d) {
  let h = (m, w) => (s[w] ? m.route.id !== s[w].route.id : !0),
    y = (m, w) => {
      var S;
      return (
        s[w].pathname !== m.pathname ||
        (((S = s[w].route.path) == null ? void 0 : S.endsWith("*")) && s[w].params["*"] !== m.params["*"])
      );
    };
  return d === "assets"
    ? u.filter((m, w) => h(m, w) || y(m, w))
    : d === "data"
      ? u.filter((m, w) => {
          var R;
          let S = c.routes[m.route.id];
          if (!S || !S.hasLoader) return !1;
          if (h(m, w) || y(m, w)) return !0;
          if (m.route.shouldRevalidate) {
            let j = m.route.shouldRevalidate({
              currentUrl: new URL(f.pathname + f.search + f.hash, window.origin),
              currentParams: ((R = s[0]) == null ? void 0 : R.params) || {},
              nextUrl: new URL(i, window.origin),
              nextParams: m.params,
              defaultShouldRevalidate: !0,
            });
            if (typeof j == "boolean") return j;
          }
          return !0;
        })
      : [];
}
function Dh(i, u, { includeHydrateFallback: s } = {}) {
  return Ih(
    i
      .map((c) => {
        let f = u.routes[c.route.id];
        if (!f) return [];
        let d = [f.module];
        return (
          f.clientActionModule && (d = d.concat(f.clientActionModule)),
          f.clientLoaderModule && (d = d.concat(f.clientLoaderModule)),
          s && f.hydrateFallbackModule && (d = d.concat(f.hydrateFallbackModule)),
          f.imports && (d = d.concat(f.imports)),
          d
        );
      })
      .flat(1)
  );
}
function Ih(i) {
  return [...new Set(i)];
}
function zh(i) {
  let u = {},
    s = Object.keys(i).sort();
  for (let c of s) u[c] = i[c];
  return u;
}
function Fh(i, u) {
  let s = new Set();
  return (
    new Set(u),
    i.reduce((c, f) => {
      let d = JSON.stringify(zh(f));
      return (s.has(d) || (s.add(d), c.push({ key: d, link: f })), c);
    }, [])
  );
}
function nf() {
  let i = C.useContext(Jn);
  return (ws(i, "You must render this element inside a <DataRouterContext.Provider> element"), i);
}
function Ah() {
  let i = C.useContext(oi);
  return (ws(i, "You must render this element inside a <DataRouterStateContext.Provider> element"), i);
}
var xs = C.createContext(void 0);
xs.displayName = "FrameworkContext";
function rf() {
  let i = C.useContext(xs);
  return (ws(i, "You must render this element inside a <HydratedRouter> element"), i);
}
function Uh(i, u) {
  let s = C.useContext(xs),
    [c, f] = C.useState(!1),
    [d, h] = C.useState(!1),
    { onFocus: y, onBlur: m, onMouseEnter: w, onMouseLeave: S, onTouchStart: R } = u,
    j = C.useRef(null);
  (C.useEffect(() => {
    if ((i === "render" && h(!0), i === "viewport")) {
      let z = ($) => {
          $.forEach((W) => {
            h(W.isIntersecting);
          });
        },
        D = new IntersectionObserver(z, { threshold: 0.5 });
      return (
        j.current && D.observe(j.current),
        () => {
          D.disconnect();
        }
      );
    }
  }, [i]),
    C.useEffect(() => {
      if (c) {
        let z = setTimeout(() => {
          h(!0);
        }, 100);
        return () => {
          clearTimeout(z);
        };
      }
    }, [c]));
  let I = () => {
      f(!0);
    },
    F = () => {
      (f(!1), h(!1));
    };
  return s
    ? i !== "intent"
      ? [d, j, {}]
      : [
          d,
          j,
          {
            onFocus: Ar(y, I),
            onBlur: Ar(m, F),
            onMouseEnter: Ar(w, I),
            onMouseLeave: Ar(S, F),
            onTouchStart: Ar(R, I),
          },
        ]
    : [!1, j, {}];
}
function Ar(i, u) {
  return (s) => {
    (i && i(s), s.defaultPrevented || u(s));
  };
}
function $h({ page: i, ...u }) {
  let { router: s } = nf(),
    c = C.useMemo(() => Uc(s.routes, i, s.basename), [s.routes, i, s.basename]);
  return c ? C.createElement(Hh, { page: i, matches: c, ...u }) : null;
}
function Bh(i) {
  let { manifest: u, routeModules: s } = rf(),
    [c, f] = C.useState([]);
  return (
    C.useEffect(() => {
      let d = !1;
      return (
        Mh(i, u, s).then((h) => {
          d || f(h);
        }),
        () => {
          d = !0;
        }
      );
    }, [i, u, s]),
    c
  );
}
function Hh({ page: i, matches: u, ...s }) {
  let c = cn(),
    { manifest: f, routeModules: d } = rf(),
    { basename: h } = nf(),
    { loaderData: y, matches: m } = Ah(),
    w = C.useMemo(() => Oc(i, u, m, f, c, "data"), [i, u, m, f, c]),
    S = C.useMemo(() => Oc(i, u, m, f, c, "assets"), [i, u, m, f, c]),
    R = C.useMemo(() => {
      if (i === c.pathname + c.search + c.hash) return [];
      let F = new Set(),
        z = !1;
      if (
        (u.forEach(($) => {
          var A;
          let W = f.routes[$.route.id];
          !W ||
            !W.hasLoader ||
            ((!w.some((le) => le.route.id === $.route.id) &&
              $.route.id in y &&
              (A = d[$.route.id]) != null &&
              A.shouldRevalidate) ||
            W.hasClientLoader
              ? (z = !0)
              : F.add($.route.id));
        }),
        F.size === 0)
      )
        return [];
      let D = Lh(i, h, "data");
      return (
        z &&
          F.size > 0 &&
          D.searchParams.set(
            "_routes",
            u
              .filter(($) => F.has($.route.id))
              .map(($) => $.route.id)
              .join(",")
          ),
        [D.pathname + D.search]
      );
    }, [h, y, c, f, w, u, i, d]),
    j = C.useMemo(() => Dh(S, f), [S, f]),
    I = Bh(S);
  return C.createElement(
    C.Fragment,
    null,
    R.map((F) => C.createElement("link", { key: F, rel: "prefetch", as: "fetch", href: F, ...s })),
    j.map((F) => C.createElement("link", { key: F, rel: "modulepreload", href: F, ...s })),
    I.map(({ key: F, link: z }) => C.createElement("link", { key: F, nonce: s.nonce, ...z }))
  );
}
function Wh(...i) {
  return (u) => {
    i.forEach((s) => {
      typeof s == "function" ? s(u) : s != null && (s.current = u);
    });
  };
}
var Vh = typeof window < "u" && typeof window.document < "u" && typeof window.document.createElement < "u";
try {
  Vh && (window.__reactRouterVersion = "7.11.0");
} catch {}
function Qh({ basename: i, children: u, unstable_useTransitions: s, window: c }) {
  let f = C.useRef();
  f.current == null && (f.current = Ep({ window: c, v5Compat: !0 }));
  let d = f.current,
    [h, y] = C.useState({ action: d.action, location: d.location }),
    m = C.useCallback(
      (w) => {
        s === !1 ? y(w) : C.startTransition(() => y(w));
      },
      [s]
    );
  return (
    C.useLayoutEffect(() => d.listen(m), [d, m]),
    C.createElement(_h, {
      basename: i,
      children: u,
      location: h.location,
      navigationType: h.action,
      navigator: d,
      unstable_useTransitions: s,
    })
  );
}
var lf = /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i,
  of = C.forwardRef(function (
    {
      onClick: u,
      discover: s = "render",
      prefetch: c = "none",
      relative: f,
      reloadDocument: d,
      replace: h,
      state: y,
      target: m,
      to: w,
      preventScrollReset: S,
      viewTransition: R,
      unstable_defaultShouldRevalidate: j,
      ...I
    },
    F
  ) {
    let { basename: z, unstable_useTransitions: D } = C.useContext(mt),
      $ = typeof w == "string" && lf.test(w),
      W = Kc(w, z);
    w = W.to;
    let A = lh(w, { relative: f }),
      [le, ie, he] = Uh(c, I),
      xe = Gh(w, {
        replace: h,
        state: y,
        target: m,
        preventScrollReset: S,
        relative: f,
        viewTransition: R,
        unstable_defaultShouldRevalidate: j,
        unstable_useTransitions: D,
      });
    function Re(ze) {
      (u && u(ze), ze.defaultPrevented || xe(ze));
    }
    let Ie = C.createElement("a", {
      ...I,
      ...he,
      href: W.absoluteURL || A,
      onClick: W.isExternal || d ? u : Re,
      ref: Wh(F, ie),
      target: m,
      "data-discover": !$ && s === "render" ? "true" : void 0,
    });
    return le && !$ ? C.createElement(C.Fragment, null, Ie, C.createElement($h, { page: A })) : Ie;
  });
of.displayName = "Link";
var Kh = C.forwardRef(function (
  {
    "aria-current": u = "page",
    caseSensitive: s = !1,
    className: c = "",
    end: f = !1,
    style: d,
    to: h,
    viewTransition: y,
    children: m,
    ...w
  },
  S
) {
  let R = Hr(h, { relative: w.relative }),
    j = cn(),
    I = C.useContext(oi),
    { navigator: F, basename: z } = C.useContext(mt),
    D = I != null && tm(R) && y === !0,
    $ = F.encodeLocation ? F.encodeLocation(R).pathname : R.pathname,
    W = j.pathname,
    A = I && I.navigation && I.navigation.location ? I.navigation.location.pathname : null;
  (s || ((W = W.toLowerCase()), (A = A ? A.toLowerCase() : null), ($ = $.toLowerCase())),
    A && z && (A = Bt(A, z) || A));
  const le = $ !== "/" && $.endsWith("/") ? $.length - 1 : $.length;
  let ie = W === $ || (!f && W.startsWith($) && W.charAt(le) === "/"),
    he = A != null && (A === $ || (!f && A.startsWith($) && A.charAt($.length) === "/")),
    xe = { isActive: ie, isPending: he, isTransitioning: D },
    Re = ie ? u : void 0,
    Ie;
  typeof c == "function"
    ? (Ie = c(xe))
    : (Ie = [c, ie ? "active" : null, he ? "pending" : null, D ? "transitioning" : null].filter(Boolean).join(" "));
  let ze = typeof d == "function" ? d(xe) : d;
  return C.createElement(
    of,
    { ...w, "aria-current": Re, className: Ie, ref: S, style: ze, to: h, viewTransition: y },
    typeof m == "function" ? m(xe) : m
  );
});
Kh.displayName = "NavLink";
var qh = C.forwardRef(
  (
    {
      discover: i = "render",
      fetcherKey: u,
      navigate: s,
      reloadDocument: c,
      replace: f,
      state: d,
      method: h = ti,
      action: y,
      onSubmit: m,
      relative: w,
      preventScrollReset: S,
      viewTransition: R,
      unstable_defaultShouldRevalidate: j,
      ...I
    },
    F
  ) => {
    let { unstable_useTransitions: z } = C.useContext(mt),
      D = bh(),
      $ = em(y, { relative: w }),
      W = h.toLowerCase() === "get" ? "get" : "post",
      A = typeof y == "string" && lf.test(y),
      le = (ie) => {
        if ((m && m(ie), ie.defaultPrevented)) return;
        ie.preventDefault();
        let he = ie.nativeEvent.submitter,
          xe = (he == null ? void 0 : he.getAttribute("formmethod")) || h,
          Re = () =>
            D(he || ie.currentTarget, {
              fetcherKey: u,
              method: xe,
              navigate: s,
              replace: f,
              state: d,
              relative: w,
              preventScrollReset: S,
              viewTransition: R,
              unstable_defaultShouldRevalidate: j,
            });
        z && s !== !1 ? C.startTransition(() => Re()) : Re();
      };
    return C.createElement("form", {
      ref: F,
      method: W,
      action: $,
      onSubmit: c ? m : le,
      ...I,
      "data-discover": !A && i === "render" ? "true" : void 0,
    });
  }
);
qh.displayName = "Form";
function Yh(i) {
  return `${i} must be used within a data router.  See https://reactrouter.com/en/main/routers/picking-a-router.`;
}
function sf(i) {
  let u = C.useContext(Jn);
  return (Ne(u, Yh(i)), u);
}
function Gh(
  i,
  {
    target: u,
    replace: s,
    state: c,
    preventScrollReset: f,
    relative: d,
    viewTransition: h,
    unstable_defaultShouldRevalidate: y,
    unstable_useTransitions: m,
  } = {}
) {
  let w = Zc(),
    S = cn(),
    R = Hr(i, { relative: d });
  return C.useCallback(
    (j) => {
      if (Ch(j, u)) {
        j.preventDefault();
        let I = s !== void 0 ? s : Ur(S) === Ur(R),
          F = () =>
            w(i, {
              replace: I,
              state: c,
              preventScrollReset: f,
              relative: d,
              viewTransition: h,
              unstable_defaultShouldRevalidate: y,
            });
        m ? C.startTransition(() => F()) : F();
      }
    },
    [S, w, R, s, c, u, i, f, d, h, y, m]
  );
}
function Xh(i) {
  ht(
    typeof URLSearchParams < "u",
    "You cannot use the `useSearchParams` hook in a browser that does not support the URLSearchParams API. If you need to support Internet Explorer 11, we recommend you load a polyfill such as https://github.com/ungap/url-search-params."
  );
  let u = C.useRef(ms(i)),
    s = C.useRef(!1),
    c = cn(),
    f = C.useMemo(() => Nh(c.search, s.current ? null : u.current), [c.search]),
    d = Zc(),
    h = C.useCallback(
      (y, m) => {
        const w = ms(typeof y == "function" ? y(new URLSearchParams(f)) : y);
        ((s.current = !0), d("?" + w, m));
      },
      [d, f]
    );
  return [f, h];
}
var Jh = 0,
  Zh = () => `__${String(++Jh)}__`;
function bh() {
  let { router: i } = sf("useSubmit"),
    { basename: u } = C.useContext(mt),
    s = mh(),
    c = i.fetch,
    f = i.navigate;
  return C.useCallback(
    async (d, h = {}) => {
      let { action: y, method: m, encType: w, formData: S, body: R } = Ph(d, u);
      if (h.navigate === !1) {
        let j = h.fetcherKey || Zh();
        await c(j, s, h.action || y, {
          unstable_defaultShouldRevalidate: h.unstable_defaultShouldRevalidate,
          preventScrollReset: h.preventScrollReset,
          formData: S,
          body: R,
          formMethod: h.method || m,
          formEncType: h.encType || w,
          flushSync: h.flushSync,
        });
      } else
        await f(h.action || y, {
          unstable_defaultShouldRevalidate: h.unstable_defaultShouldRevalidate,
          preventScrollReset: h.preventScrollReset,
          formData: S,
          body: R,
          formMethod: h.method || m,
          formEncType: h.encType || w,
          replace: h.replace,
          state: h.state,
          fromRouteId: s,
          flushSync: h.flushSync,
          viewTransition: h.viewTransition,
        });
    },
    [c, f, u, s]
  );
}
function em(i, { relative: u } = {}) {
  let { basename: s } = C.useContext(mt),
    c = C.useContext(Ht);
  Ne(c, "useFormAction must be used inside a RouteContext");
  let [f] = c.matches.slice(-1),
    d = { ...Hr(i || ".", { relative: u }) },
    h = cn();
  if (i == null) {
    d.search = h.search;
    let y = new URLSearchParams(d.search),
      m = y.getAll("index");
    if (m.some((S) => S === "")) {
      (y.delete("index"), m.filter((R) => R).forEach((R) => y.append("index", R)));
      let S = y.toString();
      d.search = S ? `?${S}` : "";
    }
  }
  return (
    (!i || i === ".") && f.route.index && (d.search = d.search ? d.search.replace(/^\?/, "?index&") : "?index"),
    s !== "/" && (d.pathname = d.pathname === "/" ? s : $t([s, d.pathname])),
    Ur(d)
  );
}
function tm(i, { relative: u } = {}) {
  let s = C.useContext(Yc);
  Ne(
    s != null,
    "`useViewTransitionState` must be used within `react-router-dom`'s `RouterProvider`.  Did you accidentally import `RouterProvider` from `react-router`?"
  );
  let { basename: c } = sf("useViewTransitionState"),
    f = Hr(i, { relative: u });
  if (!s.isTransitioning) return !1;
  let d = Bt(s.currentLocation.pathname, c) || s.currentLocation.pathname,
    h = Bt(s.nextLocation.pathname, c) || s.nextLocation.pathname;
  return ri(f.pathname, h) != null || ri(f.pathname, d) != null;
}
const nm = 1,
  li = 2,
  cs = 3,
  uf = 4,
  rm = 5,
  lm = 6;
function im(i) {
  return { type: "auth", access_token: i };
}
function om() {
  return { type: "supported_features", id: 1, features: { coalesce_messages: 1 } };
}
function sm() {
  return { type: "get_states" };
}
function um(i) {
  const u = { type: "subscribe_events" };
  return (i && (u.event_type = i), u);
}
function Mc(i) {
  return { type: "unsubscribe_events", subscription: i };
}
function am() {
  return { type: "ping" };
}
function cm(i, u) {
  return { type: "result", success: !1, error: { code: i, message: u } };
}
function fm(i) {
  const u = {},
    s = i.split("&");
  for (let c = 0; c < s.length; c++) {
    const f = s[c].split("="),
      d = decodeURIComponent(f[0]),
      h = f.length > 1 ? decodeURIComponent(f[1]) : void 0;
    u[d] = h;
  }
  return u;
}
const af = (i, u, s, c) => {
    const [f, d, h] = i.split(".", 3);
    return (
      Number(f) > u ||
      (Number(f) === u && (c === void 0 ? Number(d) >= s : Number(d) > s)) ||
      (c !== void 0 && Number(f) === u && Number(d) === s && Number(h) >= c)
    );
  },
  dm = "auth_invalid",
  pm = "auth_ok";
function hm(i) {
  if (!i.auth) throw uf;
  const u = i.auth;
  let s = u.expired
    ? u.refreshAccessToken().then(
        () => {
          s = void 0;
        },
        () => {
          s = void 0;
        }
      )
    : void 0;
  const c = u.wsUrl;
  function f(d, h, y) {
    const m = new WebSocket(c);
    let w = !1;
    const S = () => {
        if ((m.removeEventListener("close", S), w)) {
          y(li);
          return;
        }
        if (d === 0) {
          y(nm);
          return;
        }
        const I = d === -1 ? -1 : d - 1;
        setTimeout(() => f(I, h, y), 1e3);
      },
      R = async (I) => {
        try {
          (u.expired && (await (s || u.refreshAccessToken())), m.send(JSON.stringify(im(u.accessToken))));
        } catch (F) {
          ((w = F === li), m.close());
        }
      },
      j = async (I) => {
        const F = JSON.parse(I.data);
        switch (F.type) {
          case dm:
            ((w = !0), m.close());
            break;
          case pm:
            (m.removeEventListener("open", R),
              m.removeEventListener("message", j),
              m.removeEventListener("close", S),
              m.removeEventListener("error", S),
              (m.haVersion = F.ha_version),
              af(m.haVersion, 2022, 9) && m.send(JSON.stringify(om())),
              h(m));
            break;
        }
      };
    (m.addEventListener("open", R),
      m.addEventListener("message", j),
      m.addEventListener("close", S),
      m.addEventListener("error", S));
  }
  return new Promise((d, h) => f(i.setupRetry, d, h));
}
class mm {
  constructor(u, s) {
    ((this._handleMessage = (c) => {
      let f = JSON.parse(c.data);
      (Array.isArray(f) || (f = [f]),
        f.forEach((d) => {
          const h = this.commands.get(d.id);
          switch (d.type) {
            case "event":
              h
                ? h.callback(d.event)
                : (console.warn(`Received event for unknown subscription ${d.id}. Unsubscribing.`),
                  this.sendMessagePromise(Mc(d.id)).catch((y) => {}));
              break;
            case "result":
              h &&
                (d.success
                  ? (h.resolve(d.result), "subscribe" in h || this.commands.delete(d.id))
                  : (h.reject(d.error), this.commands.delete(d.id)));
              break;
            case "pong":
              h ? (h.resolve(), this.commands.delete(d.id)) : console.warn(`Received unknown pong response ${d.id}`);
              break;
          }
        }));
    }),
      (this._handleClose = async () => {
        const c = this.commands;
        if (
          ((this.commandId = 1),
          (this.oldSubscriptions = this.commands),
          (this.commands = new Map()),
          (this.socket = void 0),
          c.forEach((h) => {
            "subscribe" in h || h.reject(cm(cs, "Connection lost"));
          }),
          this.closeRequested)
        )
          return;
        this.fireEvent("disconnected");
        const f = Object.assign(Object.assign({}, this.options), { setupRetry: 0 }),
          d = (h) => {
            setTimeout(
              async () => {
                if (!this.closeRequested)
                  try {
                    const y = await f.createSocket(f);
                    this._setSocket(y);
                  } catch (y) {
                    if (this._queuedMessages) {
                      const m = this._queuedMessages;
                      this._queuedMessages = void 0;
                      for (const w of m) w.reject && w.reject(cs);
                    }
                    y === li ? this.fireEvent("reconnect-error", y) : d(h + 1);
                  }
              },
              Math.min(h, 5) * 1e3
            );
          };
        (this.suspendReconnectPromise &&
          (await this.suspendReconnectPromise, (this.suspendReconnectPromise = void 0), (this._queuedMessages = [])),
          d(0));
      }),
      (this.options = s),
      (this.commandId = 2),
      (this.commands = new Map()),
      (this.eventListeners = new Map()),
      (this.closeRequested = !1),
      this._setSocket(u));
  }
  get connected() {
    return this.socket !== void 0 && this.socket.readyState == this.socket.OPEN;
  }
  _setSocket(u) {
    ((this.socket = u),
      (this.haVersion = u.haVersion),
      u.addEventListener("message", this._handleMessage),
      u.addEventListener("close", this._handleClose));
    const s = this.oldSubscriptions;
    s &&
      ((this.oldSubscriptions = void 0),
      s.forEach((f) => {
        "subscribe" in f &&
          f.subscribe &&
          f.subscribe().then((d) => {
            ((f.unsubscribe = d), f.resolve());
          });
      }));
    const c = this._queuedMessages;
    if (c) {
      this._queuedMessages = void 0;
      for (const f of c) f.resolve();
    }
    this.fireEvent("ready");
  }
  addEventListener(u, s) {
    let c = this.eventListeners.get(u);
    (c || ((c = []), this.eventListeners.set(u, c)), c.push(s));
  }
  removeEventListener(u, s) {
    const c = this.eventListeners.get(u);
    if (!c) return;
    const f = c.indexOf(s);
    f !== -1 && c.splice(f, 1);
  }
  fireEvent(u, s) {
    (this.eventListeners.get(u) || []).forEach((c) => c(this, s));
  }
  suspendReconnectUntil(u) {
    this.suspendReconnectPromise = u;
  }
  suspend() {
    if (!this.suspendReconnectPromise) throw new Error("Suspend promise not set");
    this.socket && this.socket.close();
  }
  reconnect(u = !1) {
    if (this.socket) {
      if (!u) {
        this.socket.close();
        return;
      }
      (this.socket.removeEventListener("message", this._handleMessage),
        this.socket.removeEventListener("close", this._handleClose),
        this.socket.close(),
        this._handleClose());
    }
  }
  close() {
    ((this.closeRequested = !0), this.socket && this.socket.close());
  }
  async subscribeEvents(u, s) {
    return this.subscribeMessage(u, um(s));
  }
  ping() {
    return this.sendMessagePromise(am());
  }
  sendMessage(u, s) {
    if (!this.connected) throw cs;
    if (this._queuedMessages) {
      if (s) throw new Error("Cannot queue with commandId");
      this._queuedMessages.push({ resolve: () => this.sendMessage(u) });
      return;
    }
    (s || (s = this._genCmdId()), (u.id = s), this.socket.send(JSON.stringify(u)));
  }
  sendMessagePromise(u) {
    return new Promise((s, c) => {
      if (this._queuedMessages) {
        this._queuedMessages.push({
          reject: c,
          resolve: async () => {
            try {
              s(await this.sendMessagePromise(u));
            } catch (d) {
              c(d);
            }
          },
        });
        return;
      }
      const f = this._genCmdId();
      (this.commands.set(f, { resolve: s, reject: c }), this.sendMessage(u, f));
    });
  }
  async subscribeMessage(u, s, c) {
    if (
      (this._queuedMessages &&
        (await new Promise((d, h) => {
          this._queuedMessages.push({ resolve: d, reject: h });
        })),
      c != null && c.preCheck && !(await c.preCheck()))
    )
      throw new Error("Pre-check failed");
    let f;
    return (
      await new Promise((d, h) => {
        const y = this._genCmdId();
        ((f = {
          resolve: d,
          reject: h,
          callback: u,
          subscribe: (c == null ? void 0 : c.resubscribe) !== !1 ? () => this.subscribeMessage(u, s, c) : void 0,
          unsubscribe: async () => {
            (this.connected && (await this.sendMessagePromise(Mc(y))), this.commands.delete(y));
          },
        }),
          this.commands.set(y, f));
        try {
          this.sendMessage(s, y);
        } catch {}
      }),
      () => f.unsubscribe()
    );
  }
  _genCmdId() {
    return ++this.commandId;
  }
}
const vm = () => `${location.protocol}//${location.host}/`,
  ym = (i) => i * 1e3 + Date.now();
function gm() {
  const { protocol: i, host: u, pathname: s, search: c } = location;
  return `${i}//${u}${s}${c}`;
}
function _m(i, u, s, c) {
  let f = `${i}/auth/authorize?response_type=code&redirect_uri=${encodeURIComponent(s)}`;
  return (u !== null && (f += `&client_id=${encodeURIComponent(u)}`), c && (f += `&state=${encodeURIComponent(c)}`), f);
}
function wm(i, u, s, c) {
  ((s += (s.includes("?") ? "&" : "?") + "auth_callback=1"), (document.location.href = _m(i, u, s, c)));
}
async function cf(i, u, s) {
  const c = typeof location < "u" && location;
  if (c && c.protocol === "https:") {
    const y = document.createElement("a");
    if (((y.href = i), y.protocol === "http:" && y.hostname !== "localhost")) throw rm;
  }
  const f = new FormData();
  (u !== null && f.append("client_id", u),
    Object.keys(s).forEach((y) => {
      f.append(y, s[y]);
    }));
  const d = await fetch(`${i}/auth/token`, { method: "POST", credentials: "same-origin", body: f });
  if (!d.ok) throw d.status === 400 || d.status === 403 ? li : new Error("Unable to fetch tokens");
  const h = await d.json();
  return ((h.hassUrl = i), (h.clientId = u), (h.expires = ym(h.expires_in)), h);
}
function Dc(i, u, s) {
  return cf(i, u, { code: s, grant_type: "authorization_code" });
}
function xm(i) {
  return btoa(JSON.stringify(i));
}
function Sm(i) {
  return JSON.parse(atob(i));
}
class ff {
  constructor(u, s) {
    ((this.data = u), (this._saveTokens = s));
  }
  get wsUrl() {
    return `ws${this.data.hassUrl.substr(4)}/api/websocket`;
  }
  get accessToken() {
    return this.data.access_token;
  }
  get expired() {
    return Date.now() > this.data.expires;
  }
  async refreshAccessToken() {
    if (!this.data.refresh_token) throw new Error("No refresh_token");
    const u = await cf(this.data.hassUrl, this.data.clientId, {
      grant_type: "refresh_token",
      refresh_token: this.data.refresh_token,
    });
    ((u.refresh_token = this.data.refresh_token), (this.data = u), this._saveTokens && this._saveTokens(u));
  }
  async revoke() {
    if (!this.data.refresh_token) throw new Error("No refresh_token to revoke");
    const u = new FormData();
    (u.append("token", this.data.refresh_token),
      await fetch(`${this.data.hassUrl}/auth/revoke`, { method: "POST", credentials: "same-origin", body: u }),
      this._saveTokens && this._saveTokens(null));
  }
}
function km(i, u) {
  return new ff({
    hassUrl: i,
    clientId: null,
    expires: Date.now() + 1e11,
    refresh_token: "",
    access_token: u,
    expires_in: 1e11,
  });
}
async function Em(i = {}) {
  let u,
    s = i.hassUrl;
  s && s[s.length - 1] === "/" && (s = s.substr(0, s.length - 1));
  const c = i.clientId !== void 0 ? i.clientId : vm(),
    f = i.limitHassInstance === !0;
  if ((i.authCode && s && ((u = await Dc(s, c, i.authCode)), i.saveTokens && i.saveTokens(u)), !u)) {
    const d = fm(location.search.substr(1));
    if ("auth_callback" in d) {
      const h = Sm(d.state);
      if (f && (h.hassUrl !== s || h.clientId !== c)) throw lm;
      ((u = await Dc(h.hassUrl, h.clientId, d.code)), i.saveTokens && i.saveTokens(u));
    }
  }
  if ((!u && i.loadTokens && (u = await i.loadTokens()), u && (s === void 0 || u.hassUrl === s)))
    return new ff(u, i.saveTokens);
  if (s === void 0) throw uf;
  return (wm(s, c, i.redirectUrl || gm(), xm({ hassUrl: s, clientId: c })), new Promise(() => {}));
}
const Cm = (i) => {
    let u = [];
    function s(f) {
      let d = [];
      for (let h = 0; h < u.length; h++) u[h] === f ? (f = null) : d.push(u[h]);
      u = d;
    }
    function c(f, d) {
      i = d ? f : Object.assign(Object.assign({}, i), f);
      let h = u;
      for (let y = 0; y < h.length; y++) h[y](i);
    }
    return {
      get state() {
        return i;
      },
      action(f) {
        function d(h) {
          c(h, !1);
        }
        return function () {
          let h = [i];
          for (let m = 0; m < arguments.length; m++) h.push(arguments[m]);
          let y = f.apply(this, h);
          if (y != null) return y instanceof Promise ? y.then(d) : d(y);
        };
      },
      setState: c,
      clearState() {
        i = void 0;
      },
      subscribe(f) {
        return (
          u.push(f),
          () => {
            s(f);
          }
        );
      },
    };
  },
  Nm = 5e3,
  Ic = (i, u, s, c, f = { unsubGrace: !0 }) => {
    if (i[u]) return i[u];
    let d = 0,
      h,
      y,
      m = Cm();
    const w = () => {
        if (!s) throw new Error("Collection does not support refresh");
        return s(i).then((z) => m.setState(z, !0));
      },
      S = () =>
        w().catch((z) => {
          if (i.connected) throw z;
        }),
      R = () => {
        if (y !== void 0) {
          (clearTimeout(y), (y = void 0));
          return;
        }
        (c && (h = c(i, m)), s && (i.addEventListener("ready", S), S()), i.addEventListener("disconnected", F));
      },
      j = () => {
        ((y = void 0),
          h &&
            h.then((z) => {
              z();
            }),
          m.clearState(),
          i.removeEventListener("ready", w),
          i.removeEventListener("disconnected", F));
      },
      I = () => {
        y = setTimeout(j, Nm);
      },
      F = () => {
        y && (clearTimeout(y), j());
      };
    return (
      (i[u] = {
        get state() {
          return m.state;
        },
        refresh: w,
        subscribe(z) {
          (d++, d === 1 && R());
          const D = m.subscribe(z);
          return (
            m.state !== void 0 && setTimeout(() => z(m.state), 0),
            () => {
              (D(), d--, d || (f.unsubGrace ? I() : j()));
            }
          );
        },
      }),
      i[u]
    );
  },
  Rm = (i) => i.sendMessagePromise(sm());
function jm(i, u) {
  const s = Object.assign({}, i.state);
  if (u.a)
    for (const c in u.a) {
      const f = u.a[c];
      let d = new Date(f.lc * 1e3).toISOString();
      s[c] = {
        entity_id: c,
        state: f.s,
        attributes: f.a,
        context: typeof f.c == "string" ? { id: f.c, parent_id: null, user_id: null } : f.c,
        last_changed: d,
        last_updated: f.lu ? new Date(f.lu * 1e3).toISOString() : d,
      };
    }
  if (u.r) for (const c of u.r) delete s[c];
  if (u.c)
    for (const c in u.c) {
      let f = s[c];
      if (!f) {
        console.warn("Received state update for unknown entity", c);
        continue;
      }
      f = Object.assign({}, f);
      const { "+": d, "-": h } = u.c[c],
        y = (d == null ? void 0 : d.a) || (h == null ? void 0 : h.a),
        m = y ? Object.assign({}, f.attributes) : f.attributes;
      if (
        (d &&
          (d.s !== void 0 && (f.state = d.s),
          d.c &&
            (typeof d.c == "string"
              ? (f.context = Object.assign(Object.assign({}, f.context), { id: d.c }))
              : (f.context = Object.assign(Object.assign({}, f.context), d.c))),
          d.lc
            ? (f.last_updated = f.last_changed = new Date(d.lc * 1e3).toISOString())
            : d.lu && (f.last_updated = new Date(d.lu * 1e3).toISOString()),
          d.a && Object.assign(m, d.a)),
        h != null && h.a)
      )
        for (const w of h.a) delete m[w];
      (y && (f.attributes = m), (s[c] = f));
    }
  i.setState(s, !0);
}
const Pm = (i, u) => i.subscribeMessage((s) => jm(u, s), { type: "subscribe_entities" });
function Lm(i, u) {
  const s = i.state;
  if (s === void 0) return;
  const { entity_id: c, new_state: f } = u.data;
  if (f) i.setState({ [f.entity_id]: f });
  else {
    const d = Object.assign({}, s);
    (delete d[c], i.setState(d, !0));
  }
}
async function Tm(i) {
  const u = await Rm(i),
    s = {};
  for (let c = 0; c < u.length; c++) {
    const f = u[c];
    s[f.entity_id] = f;
  }
  return s;
}
const Om = (i, u) => i.subscribeEvents((s) => Lm(u, s), "state_changed"),
  Mm = (i) => (af(i.haVersion, 2022, 4, 0) ? Ic(i, "_ent", void 0, Pm) : Ic(i, "_ent", Tm, Om)),
  Dm = (i, u) => Mm(i).subscribe(u);
async function Im(i) {
  const u = Object.assign({ setupRetry: 0, createSocket: hm }, i),
    s = await u.createSocket(u);
  return new mm(s, u);
}
const zc = [1e3, 2e3, 4e3, 8e3, 8e3, 8e3];
class zm {
  constructor() {
    Ut(this, "connection", null);
    Ut(this, "auth", null);
    Ut(this, "state", "disconnected");
    Ut(this, "stateCallbacks", new Set());
    Ut(this, "entitiesCallbacks", new Set());
    Ut(this, "reconnectAttempt", 0);
    Ut(this, "reconnectTimer", null);
    Ut(this, "unsubscribeEntities", null);
  }
  async connect(u, s) {
    if (!(this.state === "connected" || this.state === "connecting")) {
      this.setState("connecting");
      try {
        (s
          ? (this.auth = km(u || window.location.origin, s))
          : (this.auth = await Em({ hassUrl: u || window.location.origin })),
          (this.connection = await Im({ auth: this.auth })),
          (this.reconnectAttempt = 0),
          this.setState("connected"),
          this.connection.addEventListener("disconnected", () => {
            this.handleDisconnect();
          }),
          (this.unsubscribeEntities = Dm(this.connection, (c) => {
            this.entitiesCallbacks.forEach((f) => f(c));
          })));
      } catch (c) {
        (console.error("Failed to connect to Home Assistant:", c), this.setState("error"), this.scheduleReconnect());
      }
    }
  }
  disconnect() {
    (this.reconnectTimer && (clearTimeout(this.reconnectTimer), (this.reconnectTimer = null)),
      this.unsubscribeEntities && (this.unsubscribeEntities(), (this.unsubscribeEntities = null)),
      this.connection && (this.connection.close(), (this.connection = null)),
      this.setState("disconnected"));
  }
  onStateChange(u) {
    return (this.stateCallbacks.add(u), u(this.state), () => this.stateCallbacks.delete(u));
  }
  onEntitiesChange(u) {
    return (this.entitiesCallbacks.add(u), () => this.entitiesCallbacks.delete(u));
  }
  getState() {
    return this.state;
  }
  async sendMessage(u) {
    if (!this.connection) throw new Error("Not connected to Home Assistant");
    return this.connection.sendMessagePromise(u);
  }
  async configureFlow(u, s) {
    return this.sendMessage({ type: "config_entries/flow", flow_id: u, ...s });
  }
  async getEntityRegistry() {
    return this.sendMessage({ type: "config/entity_registry/list" });
  }
  async getDeviceRegistry() {
    return this.sendMessage({ type: "config/device_registry/list" });
  }
  async getConfigEntries() {
    return this.sendMessage({ type: "config_entries/get", domain: "haeo" });
  }
  setState(u) {
    ((this.state = u), this.stateCallbacks.forEach((s) => s(u)));
  }
  handleDisconnect() {
    (this.setState("reconnecting"), this.scheduleReconnect());
  }
  scheduleReconnect() {
    this.reconnectTimer && clearTimeout(this.reconnectTimer);
    const u = zc[Math.min(this.reconnectAttempt, zc.length - 1)];
    (this.reconnectAttempt++,
      console.log(`Reconnecting to Home Assistant in ${u}ms (attempt ${this.reconnectAttempt})`),
      (this.reconnectTimer = setTimeout(() => {
        this.connect();
      }, u)));
  }
}
let fs = null;
function Ss() {
  return (fs || (fs = new zm()), fs);
}
function Fm(i) {
  const u = i.get("flow_id");
  if (!u) throw new Error("Missing flow_id parameter");
  return {
    flowId: u,
    entryId: i.get("entry_id") ?? void 0,
    subentryType: i.get("subentry_type") ?? void 0,
    subentryId: i.get("subentry_id") ?? void 0,
    source: i.get("source") ?? void 0,
    mode: i.get("mode") ?? void 0,
  };
}
async function Am(i, u) {
  return Ss().sendMessage({ type: "config_entries/flow", flow_id: i, user_input: u });
}
async function Um(i) {
  return Ss().sendMessage({ type: "config_entries/flow/progress", flow_id: i });
}
async function $m(i) {
  try {
    return (await Um(i), !0);
  } catch {
    return !1;
  }
}
function Bm(i, u) {
  const s = `haeo_draft_${i}`;
  localStorage.setItem(s, JSON.stringify(u));
}
function df(i) {
  const u = `haeo_draft_${i}`,
    s = localStorage.getItem(u);
  if (s)
    try {
      return JSON.parse(s);
    } catch {
      return null;
    }
  return null;
}
function Hm(i) {
  const u = `haeo_draft_${i}`;
  localStorage.removeItem(u);
}
const Wm = 120 * 1e3,
  Vm = 30 * 1e3,
  pf = C.createContext(null);
function Qm({ children: i }) {
  const [u] = Xh(),
    [s, c] = C.useState({}),
    [f, d] = C.useState(!0),
    [h, y] = C.useState(!1),
    [m, w] = C.useState(null),
    [S, R] = C.useState(null),
    j = C.useMemo(() => {
      try {
        return Fm(u);
      } catch (W) {
        return (console.error("Invalid flow params:", W), null);
      }
    }, [u]);
  (C.useEffect(() => {
    if (j != null && j.flowId) {
      const W = df(j.flowId);
      W && c(W);
    }
  }, [j == null ? void 0 : j.flowId]),
    C.useEffect(() => {
      if (!(j != null && j.flowId) || !f) return;
      const W = setInterval(async () => {
        (await $m(j.flowId)) || (d(!1), R("Flow expired. Your draft has been saved."));
      }, Wm);
      return () => clearInterval(W);
    }, [j == null ? void 0 : j.flowId, f]),
    C.useEffect(() => {
      if (!(j != null && j.flowId) || !f) return;
      const W = setInterval(() => {
        Object.keys(s).length > 0 && Bm(j.flowId, s);
      }, Vm);
      return () => clearInterval(W);
    }, [j == null ? void 0 : j.flowId, s, f]));
  const I = C.useCallback((W) => {
      c(W);
    }, []),
    F = C.useCallback((W, A) => {
      c((le) => ({ ...le, [W]: A }));
    }, []),
    z = C.useCallback(async () => {
      if (!(j != null && j.flowId)) {
        R("No flow ID available");
        return;
      }
      (y(!0), R(null));
      try {
        const W = await Am(j.flowId, s);
        if (
          (w(W),
          (W.type === "create_entry" || W.type === "external_step_done") && Hm(j.flowId),
          W.errors && Object.keys(W.errors).length > 0)
        ) {
          const A = Object.entries(W.errors)
            .map(([le, ie]) => `${le}: ${ie}`)
            .join(", ");
          R(A);
        }
      } catch (W) {
        const A = W instanceof Error ? W.message : "Submission failed";
        R(A);
      } finally {
        y(!1);
      }
    }, [j == null ? void 0 : j.flowId, s]),
    D = C.useCallback(() => {
      R(null);
    }, []),
    $ = {
      params: j,
      formData: s,
      isActive: f,
      isSubmitting: h,
      result: m,
      error: S,
      setFormData: I,
      updateField: F,
      submit: z,
      clearError: D,
    };
  return p.jsx(pf.Provider, { value: $, children: i });
}
function Lt() {
  const i = C.useContext(pf);
  if (!i) throw new Error("useFlow must be used within a FlowProvider");
  return i;
}
const hf = C.createContext(null);
function Km({ children: i }) {
  const [u, s] = C.useState("disconnected"),
    [c, f] = C.useState({}),
    [d, h] = C.useState([]),
    y = Ss();
  C.useEffect(() => {
    const w = y.onStateChange(s),
      S = y.onEntitiesChange(f);
    y.connect();
    const R = async () => {
      if (y.getState() === "connected")
        try {
          const F = await y.getEntityRegistry();
          h(F);
        } catch (F) {
          console.error("Failed to load entity registry:", F);
        }
    };
    R();
    const j = (F) => {
        F === "connected" && R();
      },
      I = y.onStateChange(j);
    return () => {
      (w(), S(), I());
    };
  }, [y]);
  const m = { state: u, entities: c, entityRegistry: d, connection: y, isReady: u === "connected" };
  return p.jsx(hf.Provider, { value: m, children: i });
}
function ks() {
  const i = C.useContext(hf);
  if (!i) throw new Error("useConnection must be used within a ConnectionProvider");
  return i;
}
function an({ children: i }) {
  return p.jsxs("div", {
    className: "layout",
    children: [
      p.jsx("header", {
        className: "layout__header",
        children: p.jsx("h1", { className: "layout__title", children: "HAEO Configuration" }),
      }),
      p.jsx("main", { className: "layout__main", children: i }),
    ],
  });
}
function Fc({ message: i = "Loading..." }) {
  return p.jsxs("div", {
    className: "loading-spinner",
    children: [
      p.jsx("div", {
        className: "loading-spinner__icon",
        "aria-hidden": "true",
        children: p.jsx("svg", {
          viewBox: "0 0 24 24",
          fill: "none",
          xmlns: "http://www.w3.org/2000/svg",
          children: p.jsx("circle", {
            cx: "12",
            cy: "12",
            r: "10",
            stroke: "currentColor",
            strokeWidth: "2",
            strokeLinecap: "round",
            strokeDasharray: "31.4 31.4",
          }),
        }),
      }),
      p.jsx("p", { className: "loading-spinner__message", children: i }),
    ],
  });
}
function qm() {
  const { state: i, connection: u } = ks(),
    s = () => {
      u.connect();
    };
  return p.jsxs("div", {
    className: "connection-status",
    children: [
      p.jsx("div", { className: `connection-status__indicator connection-status__indicator--${i}` }),
      p.jsxs("div", {
        className: "connection-status__content",
        children: [
          p.jsxs("h3", {
            className: "connection-status__title",
            children: [
              i === "connected" && "Connected",
              i === "connecting" && "Connecting...",
              i === "reconnecting" && "Reconnecting...",
              i === "disconnected" && "Disconnected",
              i === "error" && "Connection Error",
            ],
          }),
          p.jsxs("p", {
            className: "connection-status__message",
            children: [
              i === "error" && "Unable to connect to Home Assistant.",
              i === "disconnected" && "Not connected to Home Assistant.",
              i === "reconnecting" && "Attempting to reconnect...",
            ],
          }),
          (i === "error" || i === "disconnected") &&
            p.jsx("button", {
              type: "button",
              className: "connection-status__retry-btn",
              onClick: s,
              children: "Retry Connection",
            }),
        ],
      }),
    ],
  });
}
function fe({
  id: i,
  label: u,
  type: s = "text",
  value: c,
  onChange: f,
  placeholder: d,
  description: h,
  required: y = !1,
  disabled: m = !1,
  min: w,
  max: S,
  step: R,
  options: j = [],
  error: I,
}) {
  const F = C.useId(),
    z = C.useId(),
    D = [h ? F : null, I ? z : null].filter(Boolean).join(" ");
  return s === "checkbox"
    ? p.jsxs("div", {
        className: "form-field form-field--checkbox",
        children: [
          p.jsxs("label", {
            className: "form-field__checkbox-label",
            children: [
              p.jsx("input", {
                type: "checkbox",
                id: i,
                checked: !!c,
                onChange: ($) => f($.target.checked),
                disabled: m,
                "aria-describedby": D || void 0,
              }),
              p.jsx("span", { className: "form-field__checkbox-text", children: u }),
            ],
          }),
          h && p.jsx("p", { id: F, className: "form-field__description", children: h }),
        ],
      })
    : s === "select"
      ? p.jsxs("div", {
          className: "form-field",
          children: [
            p.jsxs("label", {
              htmlFor: i,
              className: "form-field__label",
              children: [u, y && p.jsx("span", { className: "form-field__required", children: "*" })],
            }),
            p.jsx("select", {
              id: i,
              value: String(c),
              onChange: ($) => f($.target.value),
              disabled: m,
              required: y,
              className: `form-field__select ${I ? "form-field__select--error" : ""}`,
              "aria-describedby": D || void 0,
              "aria-invalid": I ? "true" : void 0,
              children: j.map(($) => p.jsx("option", { value: $.value, children: $.label }, $.value)),
            }),
            h && p.jsx("p", { id: F, className: "form-field__description", children: h }),
            I && p.jsx("p", { id: z, className: "form-field__error", role: "alert", children: I }),
          ],
        })
      : p.jsxs("div", {
          className: "form-field",
          children: [
            p.jsxs("label", {
              htmlFor: i,
              className: "form-field__label",
              children: [u, y && p.jsx("span", { className: "form-field__required", children: "*" })],
            }),
            p.jsx("input", {
              type: s,
              id: i,
              value: String(c),
              onChange: ($) => f(s === "number" ? Number($.target.value) : $.target.value),
              placeholder: d,
              disabled: m,
              required: y,
              min: w,
              max: S,
              step: R,
              className: `form-field__input ${I ? "form-field__input--error" : ""}`,
              "aria-describedby": D || void 0,
              "aria-invalid": I ? "true" : void 0,
            }),
            h && p.jsx("p", { id: F, className: "form-field__description", children: h }),
            I && p.jsx("p", { id: z, className: "form-field__error", role: "alert", children: I }),
          ],
        });
}
function fn({
  type: i = "button",
  variant: u = "secondary",
  size: s = "medium",
  loading: c = !1,
  disabled: f = !1,
  onClick: d,
  children: h,
  className: y = "",
}) {
  const m = ["button", `button--${u}`, `button--${s}`, c ? "button--loading" : "", y].filter(Boolean).join(" ");
  return p.jsxs("button", {
    type: i,
    className: m,
    onClick: d,
    disabled: f || c,
    "aria-busy": c,
    children: [
      c && p.jsx("span", { className: "button__spinner", "aria-hidden": "true" }),
      p.jsx("span", { className: c ? "button__content--hidden" : "", children: h }),
    ],
  });
}
function Pt({ children: i, className: u = "" }) {
  return p.jsx("div", { className: `card ${u}`, children: i });
}
const ne = (i, u = "") => (typeof i == "string" ? i : u),
  ge = (i, u) => (typeof i == "number" ? i : u),
  ii = (i, u) => (typeof i == "boolean" ? i : u),
  Ge = (i, u) => (i === "entity" || i === "constant" || i === "both" ? i : u),
  Ym = [
    { value: "2_days", label: "2 Days" },
    { value: "3_days", label: "3 Days" },
    { value: "5_days", label: "5 Days (Recommended)" },
    { value: "7_days", label: "7 Days" },
    { value: "custom", label: "Custom" },
  ];
function Gm() {
  const { formData: i, updateField: u, submit: s, isSubmitting: c, error: f } = Lt(),
    d = ne(i.horizon_preset, "5_days") === "custom",
    h = (y) => {
      (y.preventDefault(), s());
    };
  return p.jsx(Pt, {
    children: p.jsxs("form", {
      className: "form",
      onSubmit: h,
      children: [
        p.jsx("h2", { className: "form__title", children: "HAEO Network Setup" }),
        p.jsx("p", {
          className: "form__description",
          children:
            "Configure your energy optimization network. You can add batteries, solar panels, and other elements after setup.",
        }),
        f && p.jsx("div", { className: "form__error", role: "alert", children: f }),
        p.jsx(fe, {
          id: "name",
          label: "Network Name",
          required: !0,
          value: ne(i.name),
          onChange: (y) => u("name", y),
          placeholder: "e.g., Home Energy System",
        }),
        p.jsx(fe, {
          id: "horizon_preset",
          label: "Optimization Horizon",
          type: "select",
          required: !0,
          value: ne(i.horizon_preset, "5_days"),
          onChange: (y) => u("horizon_preset", y),
          options: Ym,
          description:
            "How far ahead to optimize. Longer horizons provide better planning but require more forecast data.",
        }),
        d &&
          p.jsxs("div", {
            className: "form__group",
            children: [
              p.jsx("h3", { className: "form__group-title", children: "Custom Tier Configuration" }),
              p.jsx("p", {
                className: "form__group-description",
                children: "Configure the time resolution tiers for optimization.",
              }),
              p.jsxs("div", {
                className: "form__row",
                children: [
                  p.jsx(fe, {
                    id: "tier_1_count",
                    label: "Tier 1 Count",
                    type: "number",
                    value: ge(i.tier_1_count, 5),
                    onChange: (y) => u("tier_1_count", Number(y)),
                    min: 1,
                    max: 60,
                  }),
                  p.jsx(fe, {
                    id: "tier_1_duration",
                    label: "Tier 1 Duration (min)",
                    type: "number",
                    value: ge(i.tier_1_duration, 1),
                    onChange: (y) => u("tier_1_duration", Number(y)),
                    min: 1,
                    max: 60,
                  }),
                ],
              }),
              p.jsxs("div", {
                className: "form__row",
                children: [
                  p.jsx(fe, {
                    id: "tier_2_count",
                    label: "Tier 2 Count",
                    type: "number",
                    value: ge(i.tier_2_count, 11),
                    onChange: (y) => u("tier_2_count", Number(y)),
                    min: 1,
                    max: 60,
                  }),
                  p.jsx(fe, {
                    id: "tier_2_duration",
                    label: "Tier 2 Duration (min)",
                    type: "number",
                    value: ge(i.tier_2_duration, 5),
                    onChange: (y) => u("tier_2_duration", Number(y)),
                    min: 1,
                    max: 60,
                  }),
                ],
              }),
              p.jsxs("div", {
                className: "form__row",
                children: [
                  p.jsx(fe, {
                    id: "tier_3_count",
                    label: "Tier 3 Count",
                    type: "number",
                    value: ge(i.tier_3_count, 46),
                    onChange: (y) => u("tier_3_count", Number(y)),
                    min: 1,
                    max: 100,
                  }),
                  p.jsx(fe, {
                    id: "tier_3_duration",
                    label: "Tier 3 Duration (min)",
                    type: "number",
                    value: ge(i.tier_3_duration, 30),
                    onChange: (y) => u("tier_3_duration", Number(y)),
                    min: 1,
                    max: 120,
                  }),
                ],
              }),
              p.jsxs("div", {
                className: "form__row",
                children: [
                  p.jsx(fe, {
                    id: "tier_4_count",
                    label: "Tier 4 Count",
                    type: "number",
                    value: ge(i.tier_4_count, 48),
                    onChange: (y) => u("tier_4_count", Number(y)),
                    min: 1,
                    max: 168,
                  }),
                  p.jsx(fe, {
                    id: "tier_4_duration",
                    label: "Tier 4 Duration (min)",
                    type: "number",
                    value: ge(i.tier_4_duration, 60),
                    onChange: (y) => u("tier_4_duration", Number(y)),
                    min: 1,
                    max: 240,
                  }),
                ],
              }),
            ],
          }),
        p.jsx(fe, {
          id: "advanced_mode",
          label: "Advanced Mode",
          type: "checkbox",
          value: ii(i.advanced_mode, !1),
          onChange: (y) => u("advanced_mode", y),
          description: "Enable advanced configuration options like custom connections and battery sections.",
        }),
        p.jsx("div", {
          className: "form__actions",
          children: p.jsx(fn, { type: "submit", variant: "primary", loading: c, children: "Create Network" }),
        }),
      ],
    }),
  });
}
function De({
  id: i,
  label: u,
  mode: s,
  value: c,
  constantValue: f = 0,
  onChange: d,
  unit: h = "",
  description: y,
  required: m = !1,
  disabled: w = !1,
  multiple: S = !1,
  domainFilter: R,
  deviceClassFilter: j,
}) {
  const { entities: I, entityRegistry: F } = ks(),
    [z, D] = C.useState(!1),
    [$, W] = C.useState(""),
    [A, le] = C.useState(s === "constant" ? "constant" : "entity"),
    ie = C.useRef(null),
    he = C.useRef(null),
    xe = C.useMemo(() => {
      const G = {};
      for (const ee of F) G[ee.entity_id] = ee;
      return G;
    }, [F]);
  C.useEffect(() => {
    function G(ee) {
      ie.current && !ie.current.contains(ee.target) && D(!1);
    }
    return (document.addEventListener("mousedown", G), () => document.removeEventListener("mousedown", G));
  }, []);
  const Re = C.useMemo(
      () =>
        Object.entries(I)
          .filter(([G, ee]) => {
            var me, oe, U;
            if (R && R.length > 0) {
              const Y = G.split(".")[0];
              if (!R.includes(Y)) return !1;
            }
            if (j && j.length > 0) {
              const Y = (me = ee.attributes) == null ? void 0 : me.device_class;
              if (!Y || !j.includes(Y)) return !1;
            }
            if ($) {
              const Y = $.toLowerCase(),
                H =
                  ((U = (oe = ee.attributes) == null ? void 0 : oe.friendly_name) == null ? void 0 : U.toLowerCase()) ||
                  "";
              return G.toLowerCase().includes(Y) || H.includes(Y);
            }
            return !0;
          })
          .sort(([G], [ee]) => G.localeCompare(ee)),
      [I, R, j, $]
    ),
    Ie = (G) => {
      var oe;
      const ee = I[G],
        me = xe[G];
      return me != null && me.name
        ? me.name
        : (oe = ee == null ? void 0 : ee.attributes) != null && oe.friendly_name
          ? ee.attributes.friendly_name
          : G;
    },
    ze = (G) => {
      if (S) {
        const ee = Array.isArray(c) ? c : c ? [c] : [],
          me = ee.includes(G) ? ee.filter((oe) => oe !== G) : [...ee, G];
        d("entity", me);
      } else (d("entity", G), D(!1), W(""));
    },
    kt = (G) => {
      (le(G), G === "constant" ? d("constant", "", f) : d("entity", Array.isArray(c) ? c : c || ""));
    },
    st = (G) => {
      const ee = parseFloat(G.target.value) || 0;
      d("constant", "", ee);
    },
    Fe = Array.isArray(c) ? c : c ? [c] : [];
  return p.jsxs("div", {
    className: "entity-picker",
    ref: ie,
    children: [
      p.jsxs("label", {
        htmlFor: i,
        className: "entity-picker__label",
        children: [
          u,
          m && p.jsx("span", { className: "entity-picker__required", children: "*" }),
          h && p.jsxs("span", { className: "entity-picker__unit", children: ["(", h, ")"] }),
        ],
      }),
      s === "both" &&
        p.jsxs("div", {
          className: "entity-picker__mode-toggle",
          children: [
            p.jsx("button", {
              type: "button",
              className: `entity-picker__mode-btn ${A === "entity" ? "entity-picker__mode-btn--active" : ""}`,
              onClick: () => kt("entity"),
              disabled: w,
              children: "Entity",
            }),
            p.jsx("button", {
              type: "button",
              className: `entity-picker__mode-btn ${A === "constant" ? "entity-picker__mode-btn--active" : ""}`,
              onClick: () => kt("constant"),
              disabled: w,
              children: "Constant",
            }),
          ],
        }),
      (s === "constant" || (s === "both" && A === "constant")) &&
        p.jsxs("div", {
          className: "entity-picker__constant",
          children: [
            p.jsx("input", {
              type: "number",
              id: i,
              value: f,
              onChange: st,
              disabled: w,
              className: "entity-picker__constant-input",
            }),
            h && p.jsx("span", { className: "entity-picker__constant-unit", children: h }),
          ],
        }),
      (s === "entity" || (s === "both" && A === "entity")) &&
        p.jsxs("div", {
          className: "entity-picker__dropdown",
          children: [
            p.jsxs("div", {
              className: `entity-picker__trigger ${z ? "entity-picker__trigger--open" : ""}`,
              onClick: () => !w && D(!z),
              role: "combobox",
              "aria-expanded": z,
              "aria-haspopup": "listbox",
              "aria-controls": `${i}-listbox`,
              tabIndex: w ? -1 : 0,
              onKeyDown: (G) => {
                (G.key === "Enter" || G.key === " ") && (G.preventDefault(), !w && D(!z));
              },
              children: [
                Fe.length > 0
                  ? p.jsx("div", {
                      className: "entity-picker__selected",
                      children: Fe.map((G) =>
                        p.jsxs(
                          "span",
                          {
                            className: "entity-picker__chip",
                            children: [
                              Ie(G),
                              S &&
                                p.jsx("button", {
                                  type: "button",
                                  className: "entity-picker__chip-remove",
                                  onClick: (ee) => {
                                    (ee.stopPropagation(), ze(G));
                                  },
                                  "aria-label": `Remove ${Ie(G)}`,
                                  children: "×",
                                }),
                            ],
                          },
                          G
                        )
                      ),
                    })
                  : p.jsx("span", { className: "entity-picker__placeholder", children: "Select an entity..." }),
                p.jsx("span", { className: "entity-picker__arrow", children: "▼" }),
              ],
            }),
            z &&
              p.jsxs("div", {
                className: "entity-picker__menu",
                id: `${i}-listbox`,
                role: "listbox",
                children: [
                  p.jsx("div", {
                    className: "entity-picker__search",
                    children: p.jsx("input", {
                      ref: he,
                      type: "text",
                      value: $,
                      onChange: (G) => W(G.target.value),
                      placeholder: "Search entities...",
                      className: "entity-picker__search-input",
                      autoFocus: !0,
                    }),
                  }),
                  p.jsx("div", {
                    className: "entity-picker__options",
                    children:
                      Re.length === 0
                        ? p.jsx("div", { className: "entity-picker__empty", children: "No entities found" })
                        : Re.map(([G, ee]) => {
                            var me, oe;
                            return p.jsxs(
                              "div",
                              {
                                className: `entity-picker__option ${Fe.includes(G) ? "entity-picker__option--selected" : ""}`,
                                onClick: () => ze(G),
                                role: "option",
                                "aria-selected": Fe.includes(G),
                                children: [
                                  p.jsxs("div", {
                                    className: "entity-picker__option-content",
                                    children: [
                                      p.jsx("span", {
                                        className: "entity-picker__option-name",
                                        children: ((me = ee.attributes) == null ? void 0 : me.friendly_name) || G,
                                      }),
                                      p.jsx("span", { className: "entity-picker__option-id", children: G }),
                                    ],
                                  }),
                                  p.jsxs("span", {
                                    className: "entity-picker__option-state",
                                    children: [
                                      ee.state,
                                      ((oe = ee.attributes) == null ? void 0 : oe.unit_of_measurement) &&
                                        ` ${ee.attributes.unit_of_measurement}`,
                                    ],
                                  }),
                                ],
                              },
                              G
                            );
                          }),
                  }),
                ],
              }),
          ],
        }),
      y && p.jsx("p", { className: "entity-picker__description", children: y }),
    ],
  });
}
function Xm() {
  const { params: i, formData: u, updateField: s, submit: c, isSubmitting: f, error: d } = Lt(),
    h = (i == null ? void 0 : i.source) === "reconfigure",
    y = (m) => {
      (m.preventDefault(), c());
    };
  return p.jsx(Pt, {
    children: p.jsxs("form", {
      className: "form",
      onSubmit: y,
      children: [
        p.jsx("h2", { className: "form__title", children: h ? "Edit Battery" : "Add Battery" }),
        p.jsx("p", {
          className: "form__description",
          children: "Configure your battery storage system for energy optimization.",
        }),
        d && p.jsx("div", { className: "form__error", role: "alert", children: d }),
        p.jsx(fe, {
          id: "name",
          label: "Battery Name",
          required: !0,
          value: ne(u.name),
          onChange: (m) => s("name", m),
          placeholder: "e.g., Powerwall",
          disabled: h,
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Capacity & Power" }),
            p.jsx(De, {
              id: "capacity",
              label: "Capacity",
              mode: Ge(u.capacity_mode, "constant"),
              value: ne(u.capacity),
              constantValue: ge(u.capacity_value, 13.5),
              onChange: (m, w, S) => {
                (s("capacity_mode", m), s("capacity", w), S !== void 0 && s("capacity_value", S));
              },
              unit: "kWh",
              description: "Total usable energy capacity of the battery.",
            }),
            p.jsx(De, {
              id: "max_charge_power",
              label: "Max Charge Power",
              mode: Ge(u.max_charge_power_mode, "constant"),
              value: ne(u.max_charge_power),
              constantValue: ge(u.max_charge_power_value, 5),
              onChange: (m, w, S) => {
                (s("max_charge_power_mode", m),
                  s("max_charge_power", w),
                  S !== void 0 && s("max_charge_power_value", S));
              },
              unit: "kW",
              description: "Maximum power when charging.",
            }),
            p.jsx(De, {
              id: "max_discharge_power",
              label: "Max Discharge Power",
              mode: Ge(u.max_discharge_power_mode, "constant"),
              value: ne(u.max_discharge_power),
              constantValue: ge(u.max_discharge_power_value, 5),
              onChange: (m, w, S) => {
                (s("max_discharge_power_mode", m),
                  s("max_discharge_power", w),
                  S !== void 0 && s("max_discharge_power_value", S));
              },
              unit: "kW",
              description: "Maximum power when discharging.",
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "State of Charge" }),
            p.jsx(De, {
              id: "soc",
              label: "Current SOC",
              mode: "entity",
              value: ne(u.soc),
              onChange: (m, w) => {
                s("soc", w);
              },
              unit: "%",
              required: !0,
              description: "Entity providing the current state of charge.",
            }),
            p.jsxs("div", {
              className: "form__row",
              children: [
                p.jsx(fe, {
                  id: "min_soc",
                  label: "Minimum SOC",
                  type: "number",
                  value: ge(u.min_soc, 10),
                  onChange: (m) => s("min_soc", m),
                  min: 0,
                  max: 100,
                  description: "Never discharge below this level (%)",
                }),
                p.jsx(fe, {
                  id: "max_soc",
                  label: "Maximum SOC",
                  type: "number",
                  value: ge(u.max_soc, 100),
                  onChange: (m) => s("max_soc", m),
                  min: 0,
                  max: 100,
                  description: "Never charge above this level (%)",
                }),
              ],
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Efficiency" }),
            p.jsx(De, {
              id: "charge_efficiency",
              label: "Charge Efficiency",
              mode: Ge(u.charge_efficiency_mode, "constant"),
              value: ne(u.charge_efficiency),
              constantValue: ge(u.charge_efficiency_value, 95),
              onChange: (m, w, S) => {
                (s("charge_efficiency_mode", m),
                  s("charge_efficiency", w),
                  S !== void 0 && s("charge_efficiency_value", S));
              },
              unit: "%",
              description: "Percentage of input power stored.",
            }),
            p.jsx(De, {
              id: "discharge_efficiency",
              label: "Discharge Efficiency",
              mode: Ge(u.discharge_efficiency_mode, "constant"),
              value: ne(u.discharge_efficiency),
              constantValue: ge(u.discharge_efficiency_value, 95),
              onChange: (m, w, S) => {
                (s("discharge_efficiency_mode", m),
                  s("discharge_efficiency", w),
                  S !== void 0 && s("discharge_efficiency_value", S));
              },
              unit: "%",
              description: "Percentage of stored energy delivered.",
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Network Connection" }),
            p.jsx(fe, {
              id: "connection",
              label: "Connect To",
              type: "select",
              required: !0,
              value: ne(u.connection),
              onChange: (m) => s("connection", m),
              options: [{ value: "", label: "Select a node..." }],
              description: "Select the node this battery connects to.",
            }),
          ],
        }),
        p.jsx("div", {
          className: "form__actions",
          children: p.jsx(fn, {
            type: "submit",
            variant: "primary",
            loading: f,
            children: h ? "Save Changes" : "Add Battery",
          }),
        }),
      ],
    }),
  });
}
function Jm() {
  const { params: i, formData: u, updateField: s, submit: c, isSubmitting: f, error: d } = Lt(),
    h = (i == null ? void 0 : i.source) === "reconfigure",
    y = (m) => {
      (m.preventDefault(), c());
    };
  return p.jsx(Pt, {
    children: p.jsxs("form", {
      className: "form",
      onSubmit: y,
      children: [
        p.jsx("h2", { className: "form__title", children: h ? "Edit Grid Connection" : "Add Grid Connection" }),
        p.jsx("p", {
          className: "form__description",
          children: "Configure your utility grid connection for import/export pricing and limits.",
        }),
        d && p.jsx("div", { className: "form__error", role: "alert", children: d }),
        p.jsx(fe, {
          id: "name",
          label: "Grid Name",
          required: !0,
          value: ne(u.name),
          onChange: (m) => s("name", m),
          placeholder: "e.g., Utility Grid",
          disabled: h,
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Import Pricing" }),
            p.jsx(De, {
              id: "price_import",
              label: "Import Price",
              mode: Ge(u.price_import_mode, "entity"),
              value: ne(u.price_import),
              constantValue: ge(u.price_import_value, 0.3),
              onChange: (m, w, S) => {
                (s("price_import_mode", m), s("price_import", w), S !== void 0 && s("price_import_value", S));
              },
              unit: "$/kWh",
              required: !0,
              description: "Entity providing import price or a constant rate.",
            }),
            p.jsx(De, {
              id: "max_import_power",
              label: "Max Import Power",
              mode: Ge(u.max_import_power_mode, "constant"),
              value: ne(u.max_import_power),
              constantValue: ge(u.max_import_power_value, 100),
              onChange: (m, w, S) => {
                (s("max_import_power_mode", m),
                  s("max_import_power", w),
                  S !== void 0 && s("max_import_power_value", S));
              },
              unit: "kW",
              description: "Maximum power import from the grid.",
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Export Pricing" }),
            p.jsx(De, {
              id: "price_export",
              label: "Export Price",
              mode: Ge(u.price_export_mode, "entity"),
              value: ne(u.price_export),
              constantValue: ge(u.price_export_value, 0.05),
              onChange: (m, w, S) => {
                (s("price_export_mode", m), s("price_export", w), S !== void 0 && s("price_export_value", S));
              },
              unit: "$/kWh",
              description: "Entity providing export price (feed-in tariff).",
            }),
            p.jsx(De, {
              id: "max_export_power",
              label: "Max Export Power",
              mode: Ge(u.max_export_power_mode, "constant"),
              value: ne(u.max_export_power),
              constantValue: ge(u.max_export_power_value, 5),
              onChange: (m, w, S) => {
                (s("max_export_power_mode", m),
                  s("max_export_power", w),
                  S !== void 0 && s("max_export_power_value", S));
              },
              unit: "kW",
              description: "Maximum power export to the grid (feed-in limit).",
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Network Connection" }),
            p.jsx(fe, {
              id: "connection",
              label: "Connect To",
              type: "select",
              required: !0,
              value: ne(u.connection),
              onChange: (m) => s("connection", m),
              options: [{ value: "", label: "Select a node..." }],
              description: "Select the node this grid connection connects to.",
            }),
          ],
        }),
        p.jsx("div", {
          className: "form__actions",
          children: p.jsx(fn, {
            type: "submit",
            variant: "primary",
            loading: f,
            children: h ? "Save Changes" : "Add Grid",
          }),
        }),
      ],
    }),
  });
}
function Zm() {
  const { params: i, formData: u, updateField: s, submit: c, isSubmitting: f, error: d } = Lt(),
    h = (i == null ? void 0 : i.source) === "reconfigure",
    y = (m) => {
      (m.preventDefault(), c());
    };
  return p.jsx(Pt, {
    children: p.jsxs("form", {
      className: "form",
      onSubmit: y,
      children: [
        p.jsx("h2", { className: "form__title", children: h ? "Edit Solar Array" : "Add Solar Array" }),
        p.jsx("p", {
          className: "form__description",
          children: "Configure your solar generation source with forecast data.",
        }),
        d && p.jsx("div", { className: "form__error", role: "alert", children: d }),
        p.jsx(fe, {
          id: "name",
          label: "Solar Array Name",
          required: !0,
          value: ne(u.name),
          onChange: (m) => s("name", m),
          placeholder: "e.g., Roof Panels",
          disabled: h,
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Generation Forecast" }),
            p.jsx(De, {
              id: "forecast",
              label: "Solar Forecast",
              mode: "entity",
              value: ne(u.forecast),
              onChange: (m, w) => {
                s("forecast", w);
              },
              unit: "kW",
              required: !0,
              description: "Entity providing solar generation forecast (e.g., Solcast, OpenMeteo).",
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Curtailment (Optional)" }),
            p.jsx(fe, {
              id: "allow_curtailment",
              label: "Allow Curtailment",
              type: "checkbox",
              value: ii(u.allow_curtailment, !1),
              onChange: (m) => s("allow_curtailment", m),
              description: "Enable the optimizer to curtail (reduce) solar generation if beneficial.",
            }),
            ii(u.allow_curtailment, !1) &&
              p.jsx(De, {
                id: "curtailment_cost",
                label: "Curtailment Cost",
                mode: Ge(u.curtailment_cost_mode, "constant"),
                value: ne(u.curtailment_cost),
                constantValue: ge(u.curtailment_cost_value, 0),
                onChange: (m, w, S) => {
                  (s("curtailment_cost_mode", m),
                    s("curtailment_cost", w),
                    S !== void 0 && s("curtailment_cost_value", S));
                },
                unit: "$/kWh",
                description: "Cost per kWh of curtailed generation (0 = free curtailment).",
              }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Network Connection" }),
            p.jsx(fe, {
              id: "connection",
              label: "Connect To",
              type: "select",
              required: !0,
              value: ne(u.connection),
              onChange: (m) => s("connection", m),
              options: [{ value: "", label: "Select a node..." }],
              description: "Select the node this solar array connects to.",
            }),
          ],
        }),
        p.jsx("div", {
          className: "form__actions",
          children: p.jsx(fn, {
            type: "submit",
            variant: "primary",
            loading: f,
            children: h ? "Save Changes" : "Add Solar",
          }),
        }),
      ],
    }),
  });
}
const bm = [
  { value: "forecast", label: "Forecast Load (from sensor)" },
  { value: "constant", label: "Constant Load (fixed value)" },
];
function ev() {
  const { params: i, formData: u, updateField: s, submit: c, isSubmitting: f, error: d } = Lt(),
    h = (i == null ? void 0 : i.source) === "reconfigure",
    y = ne(u.load_type, "forecast"),
    m = (w) => {
      (w.preventDefault(), c());
    };
  return p.jsx(Pt, {
    children: p.jsxs("form", {
      className: "form",
      onSubmit: m,
      children: [
        p.jsx("h2", { className: "form__title", children: h ? "Edit Load" : "Add Load" }),
        p.jsx("p", {
          className: "form__description",
          children: "Configure an electrical load that consumes power from the network.",
        }),
        d && p.jsx("div", { className: "form__error", role: "alert", children: d }),
        p.jsx(fe, {
          id: "name",
          label: "Load Name",
          required: !0,
          value: ne(u.name),
          onChange: (w) => s("name", w),
          placeholder: "e.g., House Load",
          disabled: h,
        }),
        p.jsx(fe, {
          id: "load_type",
          label: "Load Type",
          type: "select",
          required: !0,
          value: y,
          onChange: (w) => s("load_type", w),
          options: bm,
          description: "How the load demand is determined.",
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Load Configuration" }),
            y === "forecast"
              ? p.jsx(De, {
                  id: "forecast",
                  label: "Load Forecast",
                  mode: "entity",
                  value: ne(u.forecast),
                  onChange: (w, S) => {
                    s("forecast", S);
                  },
                  unit: "kW",
                  required: !0,
                  description: "Entity providing load consumption forecast.",
                })
              : p.jsx(De, {
                  id: "power",
                  label: "Constant Power",
                  mode: "constant",
                  value: ne(u.power),
                  constantValue: ge(u.power_value, 1),
                  onChange: (w, S, R) => {
                    (s("power", S), R !== void 0 && s("power_value", R));
                  },
                  unit: "kW",
                  required: !0,
                  description: "Fixed power consumption.",
                }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Network Connection" }),
            p.jsx(fe, {
              id: "connection",
              label: "Connect To",
              type: "select",
              required: !0,
              value: ne(u.connection),
              onChange: (w) => s("connection", w),
              options: [{ value: "", label: "Select a node..." }],
              description: "Select the node this load connects to.",
            }),
          ],
        }),
        p.jsx("div", {
          className: "form__actions",
          children: p.jsx(fn, {
            type: "submit",
            variant: "primary",
            loading: f,
            children: h ? "Save Changes" : "Add Load",
          }),
        }),
      ],
    }),
  });
}
function tv() {
  const { params: i, formData: u, updateField: s, submit: c, isSubmitting: f, error: d } = Lt(),
    h = (i == null ? void 0 : i.source) === "reconfigure",
    y = (m) => {
      (m.preventDefault(), c());
    };
  return p.jsx(Pt, {
    children: p.jsxs("form", {
      className: "form",
      onSubmit: y,
      children: [
        p.jsx("h2", { className: "form__title", children: h ? "Edit Node" : "Add Node" }),
        p.jsx("p", {
          className: "form__description",
          children:
            "Nodes are junction points in your energy network where power flows converge. Power balance is enforced at each node.",
        }),
        d && p.jsx("div", { className: "form__error", role: "alert", children: d }),
        p.jsx(fe, {
          id: "name",
          label: "Node Name",
          required: !0,
          value: ne(u.name),
          onChange: (m) => s("name", m),
          placeholder: "e.g., Main Bus",
          disabled: h,
        }),
        p.jsx("p", {
          className: "form__description",
          style: { marginTop: "1rem" },
          children: "After creating this node, you can connect elements (batteries, solar, loads, grid) to it.",
        }),
        p.jsx("div", {
          className: "form__actions",
          children: p.jsx(fn, {
            type: "submit",
            variant: "primary",
            loading: f,
            children: h ? "Save Changes" : "Add Node",
          }),
        }),
      ],
    }),
  });
}
function nv() {
  const { params: i, formData: u, updateField: s, submit: c, isSubmitting: f, error: d } = Lt(),
    h = (i == null ? void 0 : i.source) === "reconfigure",
    y = (m) => {
      (m.preventDefault(), c());
    };
  return p.jsx(Pt, {
    children: p.jsxs("form", {
      className: "form",
      onSubmit: y,
      children: [
        p.jsx("h2", { className: "form__title", children: h ? "Edit Inverter" : "Add Inverter" }),
        p.jsx("p", {
          className: "form__description",
          children: "Configure a DC/AC inverter connecting DC sources (solar, battery) to AC loads.",
        }),
        d && p.jsx("div", { className: "form__error", role: "alert", children: d }),
        p.jsx(fe, {
          id: "name",
          label: "Inverter Name",
          required: !0,
          value: ne(u.name),
          onChange: (m) => s("name", m),
          placeholder: "e.g., Hybrid Inverter",
          disabled: h,
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Power Rating" }),
            p.jsx(De, {
              id: "max_power",
              label: "Max Power",
              mode: Ge(u.max_power_mode, "constant"),
              value: ne(u.max_power),
              constantValue: ge(u.max_power_value, 5),
              onChange: (m, w, S) => {
                (s("max_power_mode", m), s("max_power", w), S !== void 0 && s("max_power_value", S));
              },
              unit: "kW",
              description: "Maximum continuous power rating.",
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Efficiency" }),
            p.jsx(De, {
              id: "efficiency",
              label: "Conversion Efficiency",
              mode: Ge(u.efficiency_mode, "constant"),
              value: ne(u.efficiency),
              constantValue: ge(u.efficiency_value, 97),
              onChange: (m, w, S) => {
                (s("efficiency_mode", m), s("efficiency", w), S !== void 0 && s("efficiency_value", S));
              },
              unit: "%",
              description: "DC to AC conversion efficiency.",
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Connections" }),
            p.jsx(fe, {
              id: "dc_connection",
              label: "DC Side (Input)",
              type: "select",
              required: !0,
              value: ne(u.dc_connection),
              onChange: (m) => s("dc_connection", m),
              options: [{ value: "", label: "Select a node..." }],
              description: "Node for DC connections (solar, battery).",
            }),
            p.jsx(fe, {
              id: "ac_connection",
              label: "AC Side (Output)",
              type: "select",
              required: !0,
              value: ne(u.ac_connection),
              onChange: (m) => s("ac_connection", m),
              options: [{ value: "", label: "Select a node..." }],
              description: "Node for AC connections (grid, loads).",
            }),
          ],
        }),
        p.jsx("div", {
          className: "form__actions",
          children: p.jsx(fn, {
            type: "submit",
            variant: "primary",
            loading: f,
            children: h ? "Save Changes" : "Add Inverter",
          }),
        }),
      ],
    }),
  });
}
function rv() {
  const { params: i, formData: u, updateField: s, submit: c, isSubmitting: f, error: d } = Lt(),
    h = (i == null ? void 0 : i.source) === "reconfigure",
    y = (m) => {
      (m.preventDefault(), c());
    };
  return p.jsx(Pt, {
    children: p.jsxs("form", {
      className: "form",
      onSubmit: y,
      children: [
        p.jsx("h2", { className: "form__title", children: h ? "Edit Connection" : "Add Connection" }),
        p.jsx("p", {
          className: "form__description",
          children: "Create a power connection between two nodes with optional limits and efficiency.",
        }),
        d && p.jsx("div", { className: "form__error", role: "alert", children: d }),
        p.jsx(fe, {
          id: "name",
          label: "Connection Name",
          required: !0,
          value: ne(u.name),
          onChange: (m) => s("name", m),
          placeholder: "e.g., DC Bus Link",
          disabled: h,
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Connection Points" }),
            p.jsxs("div", {
              className: "form__row",
              children: [
                p.jsx(fe, {
                  id: "source",
                  label: "Source Node",
                  type: "select",
                  required: !0,
                  value: ne(u.source),
                  onChange: (m) => s("source", m),
                  options: [{ value: "", label: "Select a node..." }],
                  description: "Power flows from this node.",
                }),
                p.jsx(fe, {
                  id: "target",
                  label: "Target Node",
                  type: "select",
                  required: !0,
                  value: ne(u.target),
                  onChange: (m) => s("target", m),
                  options: [{ value: "", label: "Select a node..." }],
                  description: "Power flows to this node.",
                }),
              ],
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Power Limits" }),
            p.jsx(De, {
              id: "max_power",
              label: "Max Power",
              mode: Ge(u.max_power_mode, "constant"),
              value: ne(u.max_power),
              constantValue: ge(u.max_power_value, 100),
              onChange: (m, w, S) => {
                (s("max_power_mode", m), s("max_power", w), S !== void 0 && s("max_power_value", S));
              },
              unit: "kW",
              description: "Maximum power flow through this connection.",
            }),
            p.jsx(fe, {
              id: "bidirectional",
              label: "Bidirectional",
              type: "checkbox",
              value: ii(u.bidirectional, !0),
              onChange: (m) => s("bidirectional", m),
              description: "Allow power to flow in both directions.",
            }),
          ],
        }),
        p.jsxs("div", {
          className: "form__section",
          children: [
            p.jsx("h3", { className: "form__section-title", children: "Efficiency & Cost" }),
            p.jsx(De, {
              id: "efficiency",
              label: "Transfer Efficiency",
              mode: Ge(u.efficiency_mode, "constant"),
              value: ne(u.efficiency),
              constantValue: ge(u.efficiency_value, 100),
              onChange: (m, w, S) => {
                (s("efficiency_mode", m), s("efficiency", w), S !== void 0 && s("efficiency_value", S));
              },
              unit: "%",
              description: "Efficiency of power transfer (100% = no losses).",
            }),
            p.jsx(De, {
              id: "cost",
              label: "Transfer Cost",
              mode: Ge(u.cost_mode, "constant"),
              value: ne(u.cost),
              constantValue: ge(u.cost_value, 0),
              onChange: (m, w, S) => {
                (s("cost_mode", m), s("cost", w), S !== void 0 && s("cost_value", S));
              },
              unit: "$/kWh",
              description: "Cost per kWh of power transferred.",
            }),
          ],
        }),
        p.jsx("div", {
          className: "form__actions",
          children: p.jsx(fn, {
            type: "submit",
            variant: "primary",
            loading: f,
            children: h ? "Save Changes" : "Add Connection",
          }),
        }),
      ],
    }),
  });
}
function lv() {
  const { params: i } = Lt();
  if (!(i != null && i.subentryType))
    return p.jsx(Pt, {
      children: p.jsxs("div", {
        className: "form",
        children: [
          p.jsx("h2", { className: "form__title", children: "Unknown Element Type" }),
          p.jsx("p", { children: "No element type specified in flow parameters." }),
        ],
      }),
    });
  switch (i.subentryType) {
    case "battery":
      return p.jsx(Xm, {});
    case "grid":
      return p.jsx(Jm, {});
    case "solar":
      return p.jsx(Zm, {});
    case "load":
      return p.jsx(ev, {});
    case "node":
      return p.jsx(tv, {});
    case "inverter":
      return p.jsx(nv, {});
    case "connection":
      return p.jsx(rv, {});
    default:
      return p.jsx(Pt, {
        children: p.jsxs("div", {
          className: "form",
          children: [
            p.jsx("h2", { className: "form__title", children: "Unsupported Element" }),
            p.jsxs("p", { children: ['Element type "', i.subentryType, '" is not yet supported in this interface.'] }),
          ],
        }),
      });
  }
}
function iv({ flowId: i }) {
  const u = df(i) !== null;
  return p.jsxs("div", {
    className: "flow-expired",
    children: [
      p.jsx("div", { className: "flow-expired__icon", "aria-hidden": "true", children: "⏰" }),
      p.jsx("h2", { className: "flow-expired__title", children: "Flow Expired" }),
      p.jsx("p", {
        className: "flow-expired__message",
        children: "The configuration flow has timed out due to inactivity.",
      }),
      u &&
        p.jsx("p", {
          className: "flow-expired__draft-notice",
          children:
            "Your draft has been saved. Return to Home Assistant and start a new configuration flow to continue where you left off.",
        }),
      p.jsx("p", {
        className: "flow-expired__instructions",
        children: "Please close this window and start a new configuration flow from Home Assistant.",
      }),
    ],
  });
}
function ov({ result: i }) {
  var s;
  const u = ((s = i.result) == null ? void 0 : s.title) || "Configuration";
  return p.jsxs("div", {
    className: "flow-success",
    children: [
      p.jsx("div", { className: "flow-success__icon", "aria-hidden": "true", children: "✓" }),
      p.jsx("h2", { className: "flow-success__title", children: "Success!" }),
      p.jsxs("p", {
        className: "flow-success__message",
        children: [p.jsx("strong", { children: u }), " has been configured successfully."],
      }),
      p.jsx("p", {
        className: "flow-success__instructions",
        children: "This window will close automatically. If it doesn't, you can close it manually.",
      }),
    ],
  });
}
function sv() {
  const { state: i, isReady: u } = ks(),
    { params: s, isActive: c, result: f } = Lt();
  return i === "connecting" || i === "reconnecting"
    ? p.jsx(an, {
        children: p.jsx("div", {
          className: "flow-page flow-page--loading",
          children: p.jsx(Fc, { message: "Connecting to Home Assistant..." }),
        }),
      })
    : i === "error" || i === "disconnected"
      ? p.jsx(an, { children: p.jsx("div", { className: "flow-page flow-page--error", children: p.jsx(qm, {}) }) })
      : s
        ? c
          ? (f == null ? void 0 : f.type) === "create_entry" || (f == null ? void 0 : f.type) === "external_step_done"
            ? p.jsx(an, { children: p.jsx(ov, { result: f }) })
            : u
              ? p.jsx(an, {
                  children: p.jsx("div", {
                    className: "flow-page",
                    children: s.mode === "hub" || !s.mode ? p.jsx(Gm, {}) : p.jsx(lv, {}),
                  }),
                })
              : p.jsx(an, {
                  children: p.jsx("div", {
                    className: "flow-page flow-page--loading",
                    children: p.jsx(Fc, { message: "Loading..." }),
                  }),
                })
          : p.jsx(an, { children: p.jsx(iv, { flowId: s.flowId }) })
        : p.jsx(an, {
            children: p.jsxs("div", {
              className: "flow-page flow-page--error",
              children: [
                p.jsx("h2", { children: "Invalid Flow" }),
                p.jsx("p", { children: "Missing or invalid flow parameters in URL." }),
                p.jsx("p", { children: "This page should be opened from Home Assistant's configuration flow." }),
              ],
            }),
          });
}
function uv() {
  return p.jsx(an, {
    children: p.jsxs("div", {
      className: "not-found-page",
      children: [
        p.jsx("h1", { children: "Page Not Found" }),
        p.jsx("p", { children: "The requested page does not exist." }),
        p.jsx("p", { children: "This app should be accessed through Home Assistant's configuration flow." }),
      ],
    }),
  });
}
function av() {
  return p.jsx(Km, {
    children: p.jsx(Qm, {
      children: p.jsxs(wh, {
        children: [p.jsx(ps, { path: "/", element: p.jsx(sv, {}) }), p.jsx(ps, { path: "*", element: p.jsx(uv, {}) })],
      }),
    }),
  });
}
kp.createRoot(document.getElementById("root")).render(
  p.jsx(vp.StrictMode, { children: p.jsx(Qh, { basename: "/haeo_static", children: p.jsx(av, {}) }) })
);
//# sourceMappingURL=index.js.map
