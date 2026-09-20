-- Never recycle emoji references: an old copied message must not select a new coupon.
CREATE TABLE zernio_emoji_references (pair TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE);
