(set-logic ALL)
(declare-fun x () Int)
(assert (= (+ x x) (* x 2)))
(check-sat)
