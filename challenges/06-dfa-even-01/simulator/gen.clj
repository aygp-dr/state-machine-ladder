;; gen.clj - a core.logic log generator for challenge 06 (dfa-even-01).
;;
;; The DFA is encoded as a RELATION (deltao / runo / accepto). Run it FORWARD to
;; enumerate words the DFA accepts; add the disequality (!= final EE) to run it
;; "backward" and enumerate words it rejects. One relation yields both the valid
;; corpus and the adversarial corpus - no separate generator + checker to drift.
;; Output: lines "<accept|reject> <word>" for a differential eval of the
;; reference implementation (see eval.sh).
(ns gen (:require [clojure.core.logic :refer :all]))

;; transition facts: [state symbol next]  (state = parity of #0, #1)
(def trans '[[EE 0 OE] [EE 1 EO] [EO 0 OO] [EO 1 EE]
             [OE 0 EE] [OE 1 OO] [OO 0 EO] [OO 1 OE]])

(defn deltao [s a n] (membero [s a n] trans))

(defn runo [s w f]                       ; f = state after folding word w from s
  (conde
    [(== w ()) (== s f)]
    [(fresh [a d n] (conso a d w) (deltao s a n) (runo n d f))]))

(defn accepto [w] (runo 'EE w 'EE))                    ; forward: accepted words
(defn rejecto [w] (fresh [f] (runo 'EE w f) (!= f 'EE))) ; backward: rejected words

(defn word->str [w] (apply str w))

(let [acc (->> (run 30 [w] (accepto w)) (remove empty?) distinct (take 8))
      rej (->> (run 30 [w] (rejecto w)) (remove empty?) distinct (take 8))]
  (doseq [w acc] (println "accept" (word->str w)))
  (doseq [w rej] (println "reject" (word->str w))))
