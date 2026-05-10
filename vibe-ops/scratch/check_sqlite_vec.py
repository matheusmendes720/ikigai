import sqlite3

def check_vec():
    try:
        conn = sqlite3.connect(":memory:")
        # Try to load extension if it exists, or check for vec_version function
        # Most sqlite-vec implementations add a function like vec_version()
        res = conn.execute("SELECT name FROM pragma_function_list WHERE name = 'vec_version'").fetchone()
        if res:
            print("sqlite-vec extension is LOADED")
        else:
            print("sqlite-vec extension NOT found")
    except Exception as e:
        print(f"Error checking: {e}")

if __name__ == "__main__":
    check_vec()
