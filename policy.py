# policy.py

class Policy:

    def __init__(self):

        # pricing drivers
        self.roof_rate = 180
        self.fascia_rate = 120
        self.barge_rate = 100

        # protection layers
        self.overhead_pct = 0.12
        self.risk_pct = 0.07

        # margin target
        self.margin_pct = 0.30