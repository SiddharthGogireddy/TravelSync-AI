interface LoadingProps {
    message?: string;
}

export default function Loading({
    message = "Planning your perfect trip..."
}: LoadingProps) {
    return (
        <div
            style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                height: "100vh",
                fontSize: "24px",
                fontWeight: "bold"
            }}
        >
            {message}
        </div>
    );
}