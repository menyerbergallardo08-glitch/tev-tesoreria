export const Store = {
    user: null,
    bcvRate: 848.55,
    accounts: [],
    categories: [],
    
    init() {
        const storedUser = localStorage.getItem('tev_user');
        if (storedUser) {
            try {
                this.user = JSON.parse(storedUser);
            } catch (e) {
                this.user = null;
            }
        }
    },
    
    setUser(userData) {
        this.user = userData;
        localStorage.setItem('tev_user', JSON.stringify(userData));
    },
    
    clear() {
        this.user = null;
        this.accounts = [];
        localStorage.removeItem('tev_user');
    }
};
