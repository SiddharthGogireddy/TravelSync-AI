type Settlement = {
    from: string;
    to: string;
    amount: number;
};

type Props = {
    settlements: Settlement[];
};

export default function SettlementCard({
    settlements,
}: Props) {

    return (

        <div
            style={{
                background: "white",
                padding: 20,
                borderRadius: 12,
                boxShadow:
                    "0 2px 8px rgba(0,0,0,.15)",
            }}
        >

            <h2>Settlements</h2>

            {settlements.length === 0 ? (

                <p>
                    Everyone is settled.
                </p>

            ) : (

                settlements.map(
                    (settlement, index) => (

                        <div key={index}>

                            <b>{settlement.from}</b>

                            {" owes "}

                            <b>{settlement.to}</b>

                            {" ₹"}

                            {settlement.amount}

                        </div>

                    )
                )

            )}

        </div>

    );
}